import pygame
import sys
import json
from PIL import Image, ImageDraw

class GoBoard:
    def __init__(self, board_mask):
        self.rows = len(board_mask)
        self.cols = len(board_mask[0]) if self.rows > 0 else 0
        self.board_mask = board_mask
        self.board = [[0 for _ in range(self.cols)] for _ in range(self.rows)]
        self.captured = {'black': 0, 'white': 0}
        self.current_player = 1
        self.last_moves = {1: None, 2: None}
        self.influence_cache = None
        self.base_power = 64
        self.move_order = []
        self.prev_board = None
        self.prev_prev_board = None
        self.consecutive_passes = 0

    def get_snapshot(self):
        return {
            'board': [row.copy() for row in self.board],
            'captured': self.captured.copy(),
            'current_player': self.current_player,
            'last_moves': self.last_moves.copy(),
            'move_order': self.move_order.copy(),
        }

    def set_snapshot(self, snapshot):
        self.board = [row.copy() for row in snapshot['board']]
        self.captured = snapshot['captured'].copy()
        self.current_player = snapshot['current_player']
        self.last_moves = snapshot['last_moves'].copy()
        self.move_order = snapshot['move_order'].copy()
        self.influence_cache = None

    def is_valid_position(self, row, col):
        return 0 <= row < self.rows and 0 <= col < self.cols and self.board_mask[row][col] == 1

    def calculate_influence(self):
        if self.influence_cache is not None:
            return self.influence_cache

        influence = [[0.0 for _ in range(self.cols)] for _ in range(self.rows)]
        for r in range(self.rows):
            for c in range(self.cols):
                stone = self.board[r][c]
                if stone == 0:
                    continue
                base = self.base_power if stone == 1 else -self.base_power
                for dr in range(-3, 4):
                    for dc in range(-3, 4):
                        nr, nc = r + dr, c + dc
                        if self.is_valid_position(nr, nc):
                            distance = abs(dr) + abs(dc)
                            influence[nr][nc] += base * (0.5 ** distance)
        self.influence_cache = [[int(round(val)) for val in row] for row in influence]
        return self.influence_cache

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
                if self.is_valid_position(nr, nc):
                    if self.board[nr][nc] == 0:
                        liberties += 1
                    elif self.board[nr][nc] == player:
                        queue.append((nr, nc))
        return liberties > 0

    def place_stone(self, row, col, player):
        if not self.is_valid_position(row, col) or self.board[row][col] != 0:
            return False

        # 创建完整棋盘快照
        original_board = [r.copy() for r in self.board]
        original_captured = self.captured.copy()

        # 放置棋子
        self.board[row][col] = player
        opponent = 3 - player

        # 第一步：检查并移除对方的死棋
        dead_opponents = []
        for r in range(self.rows):
            for c in range(self.cols):
                if self.board[r][c] == opponent and not self.check_liberty(r, c, opponent):
                    dead_opponents.append((r, c))
        
        # 移除对方死棋
        for (r, c) in dead_opponents:
            self.board[r][c] = 0
            self.captured['black' if opponent == 1 else 'white'] += 1

        # 第二步：检查己方棋子是否有气（考虑刚被吃的情况）
        has_liberty = self.check_liberty(row, col, player)

        # 第三步：验证自尽规则
        if not has_liberty and len(dead_opponents) == 0:
            # 回滚状态（既没有吃掉对方棋子，自己也没有气）
            self.board = original_board
            self.captured = original_captured
            return False

        # 第四步：检查全局劫争
        if self.prev_board is not None and self.board == self.prev_board:
            self.board = original_board
            self.captured = original_captured
            return False

        # 更新游戏状态
        self.prev_prev_board = self.prev_board
        self.prev_board = original_board
        self.last_moves[player] = (row, col)
        self.move_order.append((row, col, player))
        self.current_player = 3 - player
        self.influence_cache = None
        self.consecutive_passes = 0
        return True

    def pass_turn(self):
        self.consecutive_passes += 1
        self.current_player = 3 - self.current_player

    def is_game_over(self):
        return self.consecutive_passes >= 2

class GoGame:
    def __init__(self, json_path):
        pygame.init()
        self.cell_size = 40  # 先初始化这个属性
        self.load_board_config(json_path)
        self.generate_valid_points()
        
        self.cell_size = 40
        self.window_size = self.bg_surface.get_size()
        self.screen = pygame.display.set_mode(self.window_size)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('pingfang', 24)
        self.influence_font = pygame.font.SysFont('pingfang', 16)
        self.order_font = pygame.font.SysFont('pingfang', 16)
        self.order_last_font = pygame.font.SysFont('pingfang', 16, bold=True)
        self.go_board = GoBoard(self.board_mask)
        self.running = True
        self.show_influence = False
        self.show_territory = False
        self.history = [self.go_board.get_snapshot()]
        self.redo_stack = []

    def load_board_config(self, json_path):
        with open(json_path, 'r') as f:
            config = json.load(f)
        
        self.board_mask = config['board']
        self.offset = (config['offset_x'], config['offset_y'])
        
        bg_image = Image.open(config['background'])
        scaled_size = (
            int(bg_image.width * config['scale_x']),
            int(bg_image.height * config['scale_y'])
        )
        scaled_bg = bg_image.resize(scaled_size)
        
        draw = ImageDraw.Draw(scaled_bg)
        rows = len(self.board_mask)
        cols = len(self.board_mask[0]) if rows > 0 else 0
        
        for i in range(rows):
            for j in range(cols):
                if self.board_mask[i][j] == 1:
                    x = self.offset[0] + j * self.cell_size
                    y = self.offset[1] + i * self.cell_size
                    if j < cols-1 and self.board_mask[i][j+1] == 1:
                        draw.line([(x, y), (x + self.cell_size, y)], fill='black', width=2)
                    if i < rows-1 and self.board_mask[i+1][j] == 1:
                        draw.line([(x, y), (x, y + self.cell_size)], fill='black', width=2)
        
        self.bg_surface = pygame.image.fromstring(
            scaled_bg.tobytes(), scaled_bg.size, scaled_bg.mode)

    def generate_valid_points(self):
        self.valid_points = []
        for i in range(len(self.board_mask)):
            for j in range(len(self.board_mask[0])):
                if self.board_mask[i][j] == 1:
                    x = self.offset[0] + j * self.cell_size
                    y = self.offset[1] + i * self.cell_size
                    self.valid_points.append((x, y, i, j))

    def find_nearest_point(self, pos):
        min_dist = float('inf')
        nearest = None
        for point in self.valid_points:
            dx = point[0] - pos[0]
            dy = point[1] - pos[1]
            dist = dx*dx + dy*dy
            if dist < min_dist and dist < (self.cell_size//2)**2:
                min_dist = dist
                nearest = (point[2], point[3])
        return nearest

    def draw_board(self):
        self.screen.blit(self.bg_surface, (0, 0))
        
        for point in self.valid_points:
            x, y, i, j = point
            stone = self.go_board.board[i][j]
            if stone != 0:
                color = (0, 0, 0) if stone == 1 else (255, 255, 255)
                pygame.draw.circle(self.screen, color, (x, y), self.cell_size//3)

        mouse_pos = pygame.mouse.get_pos()
        nearest = self.find_nearest_point(mouse_pos)
        if nearest:
            i, j = nearest
            if self.go_board.board[i][j] == 0:
                x = self.offset[0] + j * self.cell_size
                y = self.offset[1] + i * self.cell_size
                preview_color = (0, 0, 0, 128) if self.go_board.current_player == 1 else (255, 255, 255, 128)
                preview_surf = pygame.Surface((self.cell_size, self.cell_size), pygame.SRCALPHA)
                pygame.draw.circle(preview_surf, preview_color, (self.cell_size//2, self.cell_size//2), self.cell_size//3)
                self.screen.blit(preview_surf, (x - self.cell_size//2, y - self.cell_size//2))

        if self.show_influence:
            influence = self.go_board.calculate_influence()
            for point in self.valid_points:
                x, y, i, j = point
                value = influence[i][j]
                if value == 0:
                    continue
                text_color = (255, 255, 255) if value > 0 else (0, 0, 0)
                bg_color = (0, 0, 0) if value > 0 else (255, 255, 255)
                text = self.influence_font.render(str(value), True, text_color, bg_color)
                text_rect = text.get_rect(center=(x, y))
                self.screen.blit(text, text_rect)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_TAB]:
            latest_by_coord = {}
            for idx, (r, c, p) in enumerate(self.go_board.move_order):
                latest_by_coord[(r, c)] = idx
            qualifying = []
            for idx, (r, c, p) in enumerate(self.go_board.move_order):
                if self.go_board.board[r][c] == p and latest_by_coord.get((r, c)) == idx:
                    qualifying.append(idx)
            last_idx = max(qualifying) if qualifying else None
            
            for idx, (r, c, p) in enumerate(self.go_board.move_order):
                if self.go_board.board[r][c] == p and latest_by_coord.get((r, c)) == idx:
                    x = self.offset[0] + c * self.cell_size
                    y = self.offset[1] + r * self.cell_size
                    font = self.order_last_font if idx == last_idx else self.order_font
                    text_color = (255, 0, 0) if idx == last_idx else ((255,255,255) if p ==1 else (0,0,0))
                    order_text = font.render(str(idx+1), True, text_color)
                    self.screen.blit(order_text, (x - 8, y - 10))

        status_text = self.font.render(
            f"黑方吃子: {self.go_board.captured['black']}  "
            f"白方吃子: {self.go_board.captured['white']}  ",
            True, (0, 0, 0))
        self.screen.blit(status_text, (20, self.window_size[1]-80))
        
        hint_text = self.font.render(
            "右键: 跳过一手 | 空格: 查看势力 | ESC: 退出 | Ctrl+Z: 悔棋 | Ctrl+Y: 撤销悔棋 | 按住 TAB: 查看顺序",
            True, (0,0,0))
        self.screen.blit(hint_text, (20, self.window_size[1]-40))

    def handle_click(self, pos):
        nearest = self.find_nearest_point(pos)
        if not nearest:
            return False
        row, col = nearest
        if self.go_board.place_stone(row, col, self.go_board.current_player):
            self.history.append(self.go_board.get_snapshot())
            self.redo_stack = []
            return True
        return False

    def undo_move(self):
        if len(self.history) > 1:
            snapshot = self.history.pop()
            self.redo_stack.append(snapshot)
            self.go_board.set_snapshot(self.history[-1])

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
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.handle_click(event.pos)
                    elif event.button == 3:
                        self.go_board.pass_turn()
                        self.history.append(self.go_board.get_snapshot())
                        self.redo_stack = []
                        if self.go_board.is_game_over():
                            print("游戏结束！")
                            self.running = False
                elif event.type == pygame.KEYDOWN:
                    mods = pygame.key.get_mods()
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.show_influence = not self.show_influence
                    elif event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                        self.undo_move()
                    elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
                        self.redo_move()

            self.draw_board()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()

if __name__ == '__main__':
    # 使用示例配置文件（需自行创建）
    game = GoGame('./board/China_elec.json')
    game.run()