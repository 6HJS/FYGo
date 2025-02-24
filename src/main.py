import pygame
import sys

class GoBoard:
    def __init__(self, size=19):
        self.size = size
        self.board = [[0]*self.size for _ in range(self.size)]  # 0空 1黑 2白
        self.captured = {'black': 0, 'white': 0}
        self.current_player = 1
        self.last_moves = {1: None, 2: None}
        self.influence_cache = None  # 势力值缓存

    def calculate_influence(self):
        """计算每个格子的势力值（带缓存机制）"""
        if self.influence_cache is not None:
            return self.influence_cache
            
        influence = [[0 for _ in range(self.size)] for _ in range(self.size)]
        
        for r in range(self.size):
            for c in range(self.size):
                stone = self.board[r][c]
                if stone == 0:
                    continue
                
                # 确定基础值
                base = 19 if stone == 1 else -19
                
                # 遍历所有可能受影响的格子
                for i in range(self.size):
                    for j in range(self.size):
                        distance = abs(r - i) + abs(c - j)
                        if distance < 19:
                            contribution = (base - distance) if stone == 1 else (base + distance)
                            influence[i][j] += contribution
        
        self.influence_cache = influence
        return influence

    def is_valid_move(self, row, col, player):
        if self.board[row][col] != 0:
            return False
        if (row, col) == self.last_moves[player]:
            return False
        
        original_board = [row.copy() for row in self.board]
        self.board[row][col] = player
        opponent = 3 - player
        dead_stones = []
        
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == opponent and not self.check_liberty(r, c, opponent):
                    dead_stones.append((r, c))
        
        for (r, c) in dead_stones:
            self.board[r][c] = 0
        
        has_liberty = self.check_liberty(row, col, player)
        self.board = original_board
        return has_liberty

    def check_liberty(self, row, col, player):
        visited = set()
        queue = [(row, col)]
        liberties = 0
        
        while queue:
            r, c = queue.pop(0)
            if (r, c) in visited:
                continue
            visited.add((r, c))
            
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    if self.board[nr][nc] == 0:
                        liberties += 1
                    elif self.board[nr][nc] == player:
                        queue.append((nr, nc))
        
        return liberties > 0

    def place_stone(self, row, col, player):
        if not self.is_valid_move(row, col, player):
            return False
        
        self.board[row][col] = player
        self.remove_dead_stones(3 - player)
        self.last_moves[player] = (row, col)
        self.current_player = 3 - player
        self.influence_cache = None  # 清空缓存
        return True

    def remove_dead_stones(self, player):
        to_remove = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == player and not self.check_liberty(r, c, player):
                    to_remove.append((r, c))
        
        for r, c in to_remove:
            self.board[r][c] = 0
            self.captured['black' if player == 1 else 'white'] += 1
        
        self.influence_cache = None  # 清空缓存

    # 其他原有方法保持不变...

class GoGame:
    def __init__(self, size=19):
        pygame.init()
        self.board_size = size
        self.cell_size = 50
        self.display_count = self.board_size - 1
        self.window_size = self.board_size * self.cell_size + 100
        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 24)
        self.influence_font = pygame.font.SysFont('arial', 16)  # 势力值专用字体
        self.go_board = GoBoard(size)
        self.running = True
        self.show_influence = False  # 显示势力值开关

    def draw_board(self):
        self.screen.fill((220, 179, 92))
        start = self.cell_size // 2
        end = self.display_count * self.cell_size + start

        # 绘制网格线
        for i in range(self.display_count):
            offset = i * self.cell_size + start
            pygame.draw.line(self.screen, (0, 0, 0), (start, offset), (end, offset), 2)
            pygame.draw.line(self.screen, (0, 0, 0), (offset, start), (offset, end), 2)

        # 绘制边框
        pygame.draw.line(self.screen, (0, 0, 0), (start, start), (start, end), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (start, start), (end, start), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (end, start), (end, end), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (start, end), (end, end), 2)

        # 绘制星位
        star_points = [(3,3), (3,9), (3,15), (9,3), (9,9), (9,15), (15,3), (15,9), (15,15)]
        for r, c in star_points:
            if r < self.display_count and c < self.display_count:
                pos = (c * self.cell_size + start, r * self.cell_size + start)
                pygame.draw.circle(self.screen, (0, 0, 0), pos, 5)

        # 绘制棋子
        for r in range(self.display_count + 1):
            for c in range(self.display_count + 1):
                if self.go_board.board[r][c] != 0:
                    color = (0, 0, 0) if self.go_board.board[r][c] == 1 else (255, 255, 255)
                    pos = (c * self.cell_size + start, r * self.cell_size + start)
                    pygame.draw.circle(self.screen, color, pos, self.cell_size // 3)

        # 显示势力值
        if self.show_influence:
            influence = self.go_board.calculate_influence()
            for r in range(self.board_size):
                for c in range(self.board_size):
                    value = influence[r][c]
                    if value == 0:
                        continue
                    x = c * self.cell_size + start
                    y = r * self.cell_size + start
                    text = self.influence_font.render(str(value), True, (255, 0, 0))
                    text_rect = text.get_rect(center=(x, y))
                    self.screen.blit(text, text_rect)

        # 显示状态信息
        status_text = self.font.render(
            f"Black Captured: {self.go_board.captured['black']}  "
            f"White Captured: {self.go_board.captured['white']}  "
            f"Current: {'Black' if self.go_board.current_player == 1 else 'White'}",
            True, (0, 0, 0))
        self.screen.blit(status_text, (20, self.window_size - 80))
        hint_text = self.font.render("Right click to pass | SPACE: Influence | ESC to exit", True, (0, 0, 0))
        self.screen.blit(hint_text, (20, self.window_size - 40))

    def handle_click(self, pos):
        x, y = pos
        start = self.cell_size // 2
        edge_margin = self.cell_size // 3
        if x < start - edge_margin or x >= start + (self.display_count) * self.cell_size + edge_margin \
            or y < start - edge_margin or y >= start + (self.display_count) * self.cell_size + edge_margin:
            return False
        
        col = round((x - start) / self.cell_size)
        row = round((y - start) / self.cell_size)
        return self.go_board.place_stone(int(row), int(col), self.go_board.current_player)

    def run(self):
        while self.running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                    elif event.button == 3:
                        self.go_board.current_player = 3 - self.go_board.current_player
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.show_influence = not self.show_influence
            
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(30)
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GoGame(size=19)
    game.run()