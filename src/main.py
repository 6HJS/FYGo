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
        self.base_power = 64  # 势力基础值（可调整）
        self.move_order = []  # 记录每步落子：(row, col, player)

    def get_snapshot(self):
        """获取当前状态的快照，用于悔棋/撤销悔棋"""
        return {
            'board': [row.copy() for row in self.board],
            'captured': self.captured.copy(),
            'current_player': self.current_player,
            'last_moves': self.last_moves.copy(),
            'move_order': self.move_order.copy(),
        }

    def set_snapshot(self, snapshot):
        """设置状态为某个快照的内容"""
        self.board = [row.copy() for row in snapshot['board']]
        self.captured = snapshot['captured'].copy()
        self.current_player = snapshot['current_player']
        self.last_moves = snapshot['last_moves'].copy()
        self.move_order = snapshot['move_order'].copy()
        self.influence_cache = None

    def calculate_influence(self):
        """计算每个格子的势力值（带缓存机制，指数衰减）"""
        if self.influence_cache is not None:
            return self.influence_cache

        influence = [[0.0 for _ in range(self.size)] for _ in range(self.size)]
        for r in range(self.size):
            for c in range(self.size):
                stone = self.board[r][c]
                if stone == 0:
                    continue
                base = self.base_power if stone == 1 else -self.base_power
                for i in range(self.size):
                    for j in range(self.size):
                        distance = abs(r - i) + abs(c - j)
                        contribution = base * (0.5 ** distance)
                        influence[i][j] += contribution
        self.influence_cache = [[int(round(val)) for val in row] for row in influence]
        return self.influence_cache

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
        # 添加落子记录，不删除旧记录，这样历史编号保持不变
        self.move_order.append((row, col, player))
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

class GoGame:
    def __init__(self, size=19):
        pygame.init()
        self.board_size = size
        self.cell_size = 40
        self.display_count = self.board_size - 1
        self.window_size = self.board_size * self.cell_size + 100
        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('arial', 24)
        self.influence_font = pygame.font.SysFont('arial', 16)  # 势力值专用字体
        # 用于落子顺序的字体（普通与粗体）
        self.order_font = pygame.font.SysFont('arial', 16)
        self.order_last_font = pygame.font.SysFont('arial', 16, bold=True)
        self.go_board = GoBoard(size)
        self.running = True
        self.show_influence = False  # 显示势力值开关
        self.show_territory = False  # 显示势力范围统计悬浮层

        # 保存棋局状态的历史记录，初始状态作为第一个快照
        self.history = [self.go_board.get_snapshot()]
        self.redo_stack = []

    def draw_board(self):
        self.screen.fill((220, 179, 92))
        start = self.cell_size // 2
        edge_margin = self.cell_size // 3
        end = self.display_count * self.cell_size + start

        # 绘制网格线与边框
        for i in range(self.display_count):
            offset = i * self.cell_size + start
            pygame.draw.line(self.screen, (0, 0, 0), (start, offset), (end, offset), 2)
            pygame.draw.line(self.screen, (0, 0, 0), (offset, start), (offset, end), 2)
        pygame.draw.line(self.screen, (0, 0, 0), (start, start-1), (start, end+1), 5)
        pygame.draw.line(self.screen, (0, 0, 0), (start-1, start), (end+1, start), 5)
        pygame.draw.line(self.screen, (0, 0, 0), (end, start-1), (end, end+1), 5)
        pygame.draw.line(self.screen, (0, 0, 0), (start-1, end), (end+1, end), 5)

        # 绘制星位
        star_points = [(3,3), (3,9), (3,15), (9,3), (9,9), (9,15), (15,3), (15,9), (15,15)]
        for r, c in star_points:
            if r < self.display_count and c < self.display_count:
                pos = (c * self.cell_size + start, r * self.cell_size + start)
                pygame.draw.circle(self.screen, (0, 0, 0), pos, 5)

        # 绘制棋子
        for r in range(self.display_count+1):
            for c in range(self.display_count+1):
                if self.go_board.board[r][c] != 0:
                    color = (0, 0, 0) if self.go_board.board[r][c] == 1 else (255, 255, 255)
                    pos = (c * self.cell_size + start, r * self.cell_size + start)
                    pygame.draw.circle(self.screen, color, pos, self.cell_size // 3)

        # 显示势力值（若开启）
        if self.show_influence:
            influence = self.go_board.calculate_influence()
            for r in range(self.board_size):
                for c in range(self.board_size):
                    value = influence[r][c]
                    if value == 0:
                        continue
                    x = c * self.cell_size + start
                    y = r * self.cell_size + start
                    if value > 0:
                        text_color = (255, 255, 255)
                        bg_color = (0, 0, 0)
                    else:
                        text_color = (0, 0, 0)
                        bg_color = (255, 255, 255)
                    text = self.influence_font.render(str(value), True, text_color, bg_color)
                    text_rect = text.get_rect(center=(x, y))
                    self.screen.blit(text, text_rect)

        # 绘制预览棋子（跟随光标，半透明）
        mouse_pos = pygame.mouse.get_pos()
        x, y = mouse_pos
        if (x >= start - edge_margin and x < start + self.display_count * self.cell_size + edge_margin and
            y >= start - edge_margin and y < start + self.display_count * self.cell_size + edge_margin):
            col = round((x - start) / self.cell_size)
            row = round((y - start) / self.cell_size)
            if self.go_board.board[row][col] == 0:
                pos = (col * self.cell_size + start, row * self.cell_size + start)
                preview_color = (0, 0, 0, 128) if self.go_board.current_player == 1 else (255, 255, 255, 128)
                preview_surf = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                pygame.draw.circle(preview_surf, preview_color, (self.cell_size//2, self.cell_size//2), self.cell_size//3)
                self.screen.blit(preview_surf, (pos[0] - self.cell_size//2, pos[1] - self.cell_size//2))

        # 如果按住 Tab 键，显示落子顺序（黑子上白字，白子上黑字，最后一步粗体红字）
        keys = pygame.key.get_pressed()
        if keys[pygame.K_TAB]:
            # 先构建字典，记录每个坐标最新的记录索引（0-based）
            latest_by_coord = {}
            for i, (r, c, player) in enumerate(self.go_board.move_order):
                latest_by_coord[(r, c)] = i
            qualifying_indices = []
            for i, (r, c, player) in enumerate(self.go_board.move_order):
                if self.go_board.board[r][c] == player and latest_by_coord.get((r, c)) == i:
                    qualifying_indices.append(i)
            last_move_index = max(qualifying_indices) if qualifying_indices else None
            for i, (r, c, player) in enumerate(self.go_board.move_order):
                if self.go_board.board[r][c] == player and latest_by_coord.get((r, c)) == i:
                    pos = (c * self.cell_size + start, r * self.cell_size + start)
                    if i == last_move_index:
                        font = self.order_last_font
                        text_color = (255, 0, 0)
                    else:
                        font = self.order_font
                        text_color = (255, 255, 255) if player == 1 else (0, 0, 0)
                    order_text = font.render(str(i+1), True, text_color)
                    order_rect = order_text.get_rect(center=pos)
                    self.screen.blit(order_text, order_rect)

        # 如果显示势力范围悬浮层，则统计双方的格子数量
        if self.show_territory:
            influence = self.go_board.calculate_influence()
            black_count = white_count = neutral_count = 0
            for row in influence:
                for val in row:
                    if val > 0:
                        black_count += 1
                    elif val < 0:
                        white_count += 1
                    else:
                        neutral_count += 1
            overlay_text = f"Territory - Black: {black_count}  White: {white_count}  Neutral: {neutral_count}"
            overlay_surf = self.font.render(overlay_text, True, (0, 0, 0))
            overlay_rect = overlay_surf.get_rect(center=(self.window_size//2, 30))
            # 绘制半透明背景
            bg_surf = pygame.Surface((overlay_rect.width+20, overlay_rect.height+10), pygame.SRCALPHA)
            bg_surf.fill((200, 200, 200, 200))
            bg_rect = bg_surf.get_rect(center=(self.window_size//2, 30))
            self.screen.blit(bg_surf, bg_rect)
            self.screen.blit(overlay_surf, overlay_rect)

        # 显示状态信息和提示
        status_text = self.font.render(
            f"Black Captured: {self.go_board.captured['black']}  "
            f"White Captured: {self.go_board.captured['white']}  "
            f"Current: {'Black' if self.go_board.current_player==1 else 'White'}",
            True, (0, 0, 0))
        self.screen.blit(status_text, (20, self.window_size-80))
        hint_text = self.font.render("Right click: pass | SPACE: Influence | ESC: exit | Ctrl+Z: Undo | Ctrl+Y: Redo | Hold TAB: Move Order | Ctrl+J: Toggle Territory", True, (0,0,0))
        self.screen.blit(hint_text, (20, self.window_size-40))

    def handle_click(self, pos):
        x, y = pos
        start = self.cell_size // 2
        edge_margin = self.cell_size // 3
        if x < start - edge_margin or x >= start + self.display_count * self.cell_size + edge_margin or \
           y < start - edge_margin or y >= start + self.display_count * self.cell_size + edge_margin:
            return False
        col = round((x - start) / self.cell_size)
        row = round((y - start) / self.cell_size)
        if self.go_board.place_stone(int(row), int(col), self.go_board.current_player):
            self.history.append(self.go_board.get_snapshot())
            self.redo_stack = []
            return True
        return False

    def undo_move(self):
        if len(self.history) > 1:
            snapshot = self.history.pop()
            self.redo_stack.append(snapshot)
            last_snapshot = self.history[-1]
            self.go_board.set_snapshot(last_snapshot)

    def redo_move(self):
        if self.redo_stack:
            snapshot = self.redo_stack.pop()
            self.history.append(snapshot)
            self.go_board.set_snapshot(snapshot)

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
                        self.history.append(self.go_board.get_snapshot())
                        self.redo_stack = []
                if event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.show_influence = not self.show_influence
                    elif event.key == pygame.K_j and (mods & pygame.KMOD_CTRL):
                        self.show_territory = not self.show_territory
                    elif event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                        self.undo_move()
                    elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
                        self.redo_move()
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GoGame(size=19)
    game.run()
