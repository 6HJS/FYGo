import pygame
import sys

class GoBoard:
    def __init__(self, size=19):
        self.size = size  # 棋盘逻辑大小为 size x size
        self.board = [[0]*self.size for _ in range(self.size)]  # 0空 1黑 2白
        self.captured = {'black': 0, 'white': 0}
        self.current_player = 1  # 黑棋先行
        self.last_moves = {1: None, 2: None}  # 分别记录黑棋和白棋的上次落子位置

    def is_valid_move(self, row, col, player):
        if self.board[row][col] != 0:
            return False
        # 检查是否与当前玩家上次落子位置相同
        if (row, col) == self.last_moves[player]:
            return False
        # 保存原始棋盘状态
        original_board = [row.copy() for row in self.board]
        # 临时放置棋子
        self.board[row][col] = player
        # 找到对手的死子
        opponent = 3 - player
        dead_stones = []
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == opponent and not self.check_liberty(r, c, opponent):
                    dead_stones.append((r, c))
        # 移除对手的死子
        for (r, c) in dead_stones:
            self.board[r][c] = 0
        # 检查当前棋子的块是否有气
        has_liberty = self.check_liberty(row, col, player)
        # 恢复棋盘状态
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
        self.remove_dead_stones(3 - player)  # 检查对手棋子
        self.last_moves[player] = (row, col)  # 更新当前玩家的上次落子位置
        self.current_player = 3 - player  # 切换玩家
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

    def calculate_territory(self):
        territory = {'black': 0, 'white': 0}
        visited = [[False]*self.size for _ in range(self.size)]
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == 0 and not visited[r][c]:
                    area, owner = self._check_area(r, c, visited)
                    if owner:
                        territory[owner] += area
        territory['black'] += self.captured['white']
        territory['white'] += self.captured['black']
        return territory

    def _check_area(self, r, c, visited):
        queue = [(r, c)]
        area = 0
        borders = set()
        while queue:
            x, y = queue.pop(0)
            if visited[x][y]:
                continue
            visited[x][y] = True
            area += 1
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if 0 <= nx < self.size and 0 <= ny < self.size:
                    if self.board[nx][ny] == 0:
                        queue.append((nx, ny))
                    else:
                        borders.add(self.board[nx][ny])
        if len(borders) == 1:
            owner = 'black' if 1 in borders else 'white'
            return area, owner
        return 0, None

class GoGame:
    def __init__(self, size=19):
        pygame.init()
        self.board_size = size          # 棋盘逻辑大小为 size x size
        self.cell_size = 50
        # 显示区域：去掉最右侧和最下侧的一行/列
        self.display_count = self.board_size - 1
        self.window_size = self.board_size * self.cell_size + 100
        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 24)
        self.go_board = GoBoard(size)
        self.running = True

    def draw_board(self):
        self.screen.fill((220, 179, 92))  # 木质背景色
        start = self.cell_size // 2
        end = self.display_count * self.cell_size + start

        # 绘制网格线（仅绘制 display_count 行和列）
        for i in range(self.display_count):
            offset = i * self.cell_size + start
            pygame.draw.line(self.screen, (0, 0, 0), (start, offset), (end, offset), 2)
            pygame.draw.line(self.screen, (0, 0, 0), (offset, start), (offset, end), 2)

        # 绘制边框线
        pygame.draw.line(self.screen, (0, 0, 0), (start, start), (start, end), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (start, start), (end, start), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (end, start), (end, end), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (start, end), (end, end), 2)

        # 绘制天元和星位（仅在显示区域内绘制）
        star_points = [(3,3), (3,9), (3,15), (9,3), (9,9), (9,15), (15,3), (15,9), (15,15)]
        for r, c in star_points:
            if r < self.display_count and c < self.display_count:
                pos = (c * self.cell_size + start, r * self.cell_size + start)
                if (r, c) == (9, 9):
                    pygame.draw.circle(self.screen, (0, 0, 0), pos, 8)
                else:
                    pygame.draw.circle(self.screen, (0, 0, 0), pos, 5)

        # 绘制棋子，仅绘制显示区域内的棋子
        for r in range(self.display_count + 1):
            for c in range(self.display_count + 1):
                if self.go_board.board[r][c] != 0:
                    color = (0, 0, 0) if self.go_board.board[r][c] == 1 else (255, 255, 255)
                    pos = (c * self.cell_size + start, r * self.cell_size + start)
                    pygame.draw.circle(self.screen, color, pos, self.cell_size // 3)

        # 显示提子数和当前玩家信息
        status_text = self.font.render(
            f"Black Captured: {self.go_board.captured['black']}  "
            f"White Captured: {self.go_board.captured['white']}  "
            f"Current: {'Black' if self.go_board.current_player == 1 else 'White'}",
            True, (0, 0, 0))
        self.screen.blit(status_text, (20, self.window_size - 80))
        hint_text = self.font.render("Right click to pass | ESC to exit", True, (0, 0, 0))
        self.screen.blit(hint_text, (20, self.window_size - 40))

    def handle_click(self, pos):
        x, y = pos
        start = self.cell_size // 2
        board_width = self.display_count * self.cell_size
        edge_margin = self.cell_size // 3
        if x < start - edge_margin or x >= start + board_width + edge_margin or y < start - edge_margin or y >= start + board_width + edge_margin:
            return False
        col = round((x) // self.cell_size)
        row = round((y) // self.cell_size)
        return self.go_board.place_stone(int(row), int(col), self.go_board.current_player)

    def show_result(self):
        territory = self.go_board.calculate_territory()
        result = f"Black: {territory['black']}  White: {territory['white']}"
        result_text = self.font.render(result, True, (255, 0, 0))
        text_rect = result_text.get_rect(center=(self.window_size // 2, self.window_size // 2))
        self.screen.blit(result_text, text_rect)
        pygame.display.flip()
        pygame.time.wait(3000)

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
                        self.show_result()
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GoGame(size=19)
    game.run()