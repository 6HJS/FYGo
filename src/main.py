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
            'board': [row.copy() for row in self.board],  # 复制当前棋盘状态
            'captured': self.captured.copy(),  # 复制当前已捕获的棋子
            'current_player': self.current_player,  # 复制当前玩家
            'last_moves': self.last_moves.copy(),  # 复制最近几步的棋子
            'move_order': self.move_order.copy(),  # 复制当前棋子的顺序
        }

    def set_snapshot(self, snapshot):
        """设置状态为某个快照的内容"""
        # 将快照中的board复制到当前对象的board属性中
        self.board = [row.copy() for row in snapshot['board']]
        # 将快照中的captured复制到当前对象的captured属性中
        self.captured = snapshot['captured'].copy()
        # 将快照中的current_player复制到当前对象的current_player属性中
        self.current_player = snapshot['current_player']
        # 将快照中的last_moves复制到当前对象的last_moves属性中
        self.last_moves = snapshot['last_moves'].copy()
        # 将快照中的move_order复制到当前对象的move_order属性中
        self.move_order = snapshot['move_order'].copy()
        # 将influence_cache属性设置为None
        self.influence_cache = None

    def calculate_influence(self):
        """计算每个格子的势力值（带缓存机制，指数衰减）"""
        # 如果缓存不为空，则直接返回缓存
        if self.influence_cache is not None:
            return self.influence_cache

        # 初始化势力值矩阵
        influence = [[0.0 for _ in range(self.size)] for _ in range(self.size)]
        # 遍历每个格子
        for r in range(self.size):
            for c in range(self.size):
                stone = self.board[r][c]
                # 如果格子为空，则跳过
                if stone == 0:
                    continue
                # 根据石头的类型确定基础势力值
                base = self.base_power if stone == 1 else -self.base_power
                # 遍历每个格子，计算势力值
                for i in range(self.size):
                    for j in range(self.size):
                        distance = abs(r - i) + abs(c - j)
                        contribution = base * (0.5 ** distance)
                        influence[i][j] += contribution
        # 将计算结果存入缓存
        self.influence_cache = [[int(round(val)) for val in row] for row in influence]
        # 返回缓存
        return self.influence_cache

    def is_valid_move(self, row, col, player):
        # 检查该位置是否已经有棋子
        if self.board[row][col] != 0:
            return False
        # 检查该位置是否是上一步的最后一个位置
        if (row, col) == self.last_moves[player]:
            return False

        # 备份当前棋盘
        original_board = [row.copy() for row in self.board]
        # 在该位置下棋
        self.board[row][col] = player
        # 计算对手
        opponent = 3 - player
        # 记录被吃掉的棋子
        dead_stones = []
        # 遍历棋盘，检查对手的棋子是否有气
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == opponent and not self.check_liberty(r, c, opponent):
                    dead_stones.append((r, c))
        # 将被吃掉的棋子置为0
        for (r, c) in dead_stones:
            self.board[r][c] = 0
        # 检查该位置是否有气
        has_liberty = self.check_liberty(row, col, player)
        # 恢复棋盘
        self.board = original_board
        # 返回该位置是否有气
        return has_liberty

    def check_liberty(self, row, col, player):
        # 定义一个集合，用于存储已经访问过的位置
        visited = set()
        # 定义一个队列，用于存储待访问的位置
        queue = [(row, col)]
        # 定义一个变量，用于记录棋子的自由度
        liberties = 0
        # 当队列不为空时，循环执行以下操作
        while queue:
            # 从队列中取出一个位置
            r, c = queue.pop(0)
            # 如果该位置已经访问过，则跳过
            if (r, c) in visited:
                continue
            # 将该位置添加到已访问集合中
            visited.add((r, c))
            # 遍历该位置的上下左右四个方向
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                # 计算该方向上的新位置
                nr, nc = r + dr, c + dc
                # 如果新位置在棋盘范围内
                if 0 <= nr < self.size and 0 <= nc < self.size:
                    # 如果新位置上的棋子为空，则自由度加一
                    if self.board[nr][nc] == 0:
                        liberties += 1
                    # 如果新位置上的棋子为当前玩家，则将该位置添加到待访问队列中
                    elif self.board[nr][nc] == player:
                        queue.append((nr, nc))
        # 返回自由度是否大于0
        return liberties > 0

    def place_stone(self, row, col, player):
        # 判断落子是否合法
        if not self.is_valid_move(row, col, player):
            return False
        # 在棋盘上落子
        self.board[row][col] = player
        # 移除死子
        self.remove_dead_stones(3 - player)
        # 记录当前玩家和落子位置
        self.last_moves[player] = (row, col)
        # 添加落子记录，不删除旧记录，这样历史编号保持不变
        self.move_order.append((row, col, player))
        # 切换当前玩家
        self.current_player = 3 - player
        self.influence_cache = None  # 清空缓存
        return True

    def remove_dead_stones(self, player):
        # 定义一个空列表，用于存储要移除的棋子
        to_remove = []
        # 遍历棋盘上的每一个位置
        for r in range(self.size):
            for c in range(self.size):
                # 如果当前位置的棋子是当前玩家，并且没有 liberties，则将该位置加入要移除的列表
                if self.board[r][c] == player and not self.check_liberty(r, c, player):
                    to_remove.append((r, c))
        # 遍历要移除的列表，将棋子移除，并更新被捕获的棋子数量
        for r, c in to_remove:
            self.board[r][c] = 0
            self.captured['black' if player == 1 else 'white'] += 1
        self.influence_cache = None  # 清空缓存

class GoGame:
    def __init__(self, size=19):
        # 初始化pygame
        pygame.init()
        # 设置棋盘大小
        self.board_size = size
        # 设置每个格子的大小
        self.cell_size = 40
        # 设置显示的格子数
        self.display_count = self.board_size - 1
        # 设置窗口大小
        self.window_size = self.board_size * self.cell_size + 100
        # 创建窗口
        self.screen = pygame.display.set_mode((self.window_size, self.window_size))
        # 设置时钟
        self.clock = pygame.time.Clock()
        # 设置字体
        self.font = pygame.font.SysFont('pingfang', 24)
        self.influence_font = pygame.font.SysFont('pingfang', 16)  # 势力值专用字体
        # 用于落子顺序的字体（普通与粗体）
        self.order_font = pygame.font.SysFont('pingfang', 16)
        self.order_last_font = pygame.font.SysFont('pingfang', 16, bold=True)
        # 创建棋盘
        self.go_board = GoBoard(size)
        # 设置运行状态
        self.running = True
        self.show_influence = False  # 显示势力值开关
        self.show_territory = False  # 显示势力范围统计悬浮层

        # 保存棋局状态的历史记录，初始状态作为第一个快照
        self.history = [self.go_board.get_snapshot()]
        self.redo_stack = []

    def draw_board(self):
        # 填充背景色
        self.screen.fill((220, 179, 92))
        # 计算起始位置和边距
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
                pos = (c * self.cell_size + start + 1, r * self.cell_size + start + 1)
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
            overlay_text = f"势力统计 - 黑方: {black_count}  白方: {white_count}  中立: {neutral_count}"
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
            f"黑方吃子: {self.go_board.captured['black']}  "
            f"白方吃子: {self.go_board.captured['white']}  ",
            True, (0, 0, 0))
        self.screen.blit(status_text, (20, self.window_size-80))
        hint_text = self.font.render("右键: 跳过一手 | 空格: 查看势力 | ESC: 退出 | Ctrl+Z: 悔棋 | Ctrl+Y: 撤销悔棋 | 按住 TAB: 查看顺序 | Ctrl+J: 统计势力", True, (0,0,0))
        self.screen.blit(hint_text, (20, self.window_size-40))

    def handle_click(self, pos):
        # 获取点击位置的坐标
        x, y = pos
        # 计算棋盘的起始位置
        start = self.cell_size // 2
        # 计算棋盘边缘的空白区域
        edge_margin = self.cell_size // 3
        # 判断点击位置是否在棋盘范围内
        if x < start - edge_margin or x >= start + self.display_count * self.cell_size + edge_margin or \
           y < start - edge_margin or y >= start + self.display_count * self.cell_size + edge_margin:
            return False
        # 计算点击位置对应的棋盘列
        col = round((x - start) / self.cell_size)
        # 计算点击位置对应的棋盘行
        row = round((y - start) / self.cell_size)
        # 在棋盘上放置棋子
        if self.go_board.place_stone(int(row), int(col), self.go_board.current_player):
            # 将当前棋盘状态添加到历史记录中
            self.history.append(self.go_board.get_snapshot())
            # 清空重做栈
            self.redo_stack = []
            return True
        return False

    def undo_move(self):
        # 如果历史记录长度大于1，则执行撤销操作
        if len(self.history) > 1:
            # 弹出历史记录中的最后一个快照
            snapshot = self.history.pop()
            # 将弹出的快照添加到redo_stack中
            self.redo_stack.append(snapshot)
            # 获取历史记录中的倒数第二个快照
            last_snapshot = self.history[-1]
            # 将倒数第二个快照设置为当前快照
            self.go_board.set_snapshot(last_snapshot)

    def redo_move(self):
        # 如果redo_stack不为空
        if self.redo_stack:
            # 弹出redo_stack中的最后一个元素，赋值给snapshot
            snapshot = self.redo_stack.pop()
            # 将snapshot添加到history中
            self.history.append(snapshot)
            # 将snapshot设置为go_board的快照
            self.go_board.set_snapshot(snapshot)

    def run(self):
        # 循环运行游戏
        while self.running:
            # 获取事件
            for event in pygame.event.get():
                # 如果事件类型为退出
                if event.type == pygame.QUIT:
                    # 设置运行状态为False
                    self.running = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    # 如果鼠标左键被按下
                    if event.button == 1:
                        # 处理点击事件
                        self.handle_click(event.pos)
                    # 如果鼠标右键被按下
                    elif event.button == 3:
                        # 切换当前玩家
                        self.go_board.current_player = 3 - self.go_board.current_player
                        # 添加当前棋盘快照到历史记录
                        self.history.append(self.go_board.get_snapshot())
                        # 清空重做栈
                        self.redo_stack = []
                if event.type == pygame.KEYDOWN:
                    # 获取键盘修饰符
                    mods = pygame.key.get_mods()
                    # 如果按下的是ESC键
                    if event.key == pygame.K_ESCAPE:
                        # 设置运行状态为False
                        self.running = False
                    # 如果按下的是空格键
                    elif event.key == pygame.K_SPACE:
                        # 切换显示影响力
                        self.show_influence = not self.show_influence
                    # 如果按下的是Ctrl+j键
                    elif event.key == pygame.K_j and (mods & pygame.KMOD_CTRL):
                        # 切换显示领土
                        self.show_territory = not self.show_territory
                    # 如果按下的是Ctrl+z键
                    elif event.key == pygame.K_z and (mods & pygame.KMOD_CTRL):
                        # 撤销一步
                        self.undo_move()
                    # 如果按下的是Ctrl+y键
                    elif event.key == pygame.K_y and (mods & pygame.KMOD_CTRL):
                        # 重做一步
                        self.redo_move()
            self.draw_board()
            pygame.display.flip()
            self.clock.tick(30)
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = GoGame(size=19)
    game.run()
