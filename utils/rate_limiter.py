import time
from collections import deque
from threading import Lock

class RateLimiter:
    def __init__(self, max_requests, time_window):
        """
        初始化限流器
        :param max_requests: 时间窗口内允许的最大请求数
        :param time_window: 时间窗口大小（秒）
        """
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
        self.lock = Lock()

    def acquire(self):
        """
        获取令牌，如果超过限制则等待
        :return: 等待时间（秒）
        """
        with self.lock:
            now = time.time()
            
            # 移除时间窗口外的请求记录
            while self.requests and self.requests[0] <= now - self.time_window:
                self.requests.popleft()
            
            # 如果当前请求数达到限制
            if len(self.requests) >= self.max_requests:
                # 计算需要等待的时间
                wait_time = self.requests[0] + self.time_window - now
                if wait_time > 0:
                    time.sleep(wait_time)
                    now = time.time()
                    # 重新清理过期的请求记录
                    while self.requests and self.requests[0] <= now - self.time_window:
                        self.requests.popleft()
            
            # 添加新的请求时间戳
            self.requests.append(now)
            return len(self.requests) 