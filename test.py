import datetime
import time
from comm.dbopper import  MyDBConn

class Test(object):
    def __init__(self):
        self.dc = MyDBConn(2)

    def find_drawdown_events(self,drawdown_list, A, B):
        events = []  # 存储符合条件的事件
        event_count = 0  # 符合条件的事件序号

        start_time = None  # 记录事件的开始时间

        for i, (max_dd, current_dd, time) in enumerate(drawdown_list):
            # 检查当前回撤是否小于A，并且之前没有开始记录
            if current_dd > A and start_time is None:
                start_time = time  # 记录事件的开始时间
            # 检查当前回撤是否大于B，并且已经有开始时间
            elif current_dd < B and start_time is not None:
                end_time = time  # 记录事件的结束时间
                events.append((event_count, start_time, end_time))  # 保存事件
                event_count += 1  # 增加事件序号
                start_time = None  # 重置开始时间

        return events

    def get_data(self):
        self.profit_data = self.dc.QueryProfit()
        x = 0
        self.winner_data = [(equity - x, time) for equity, time in self.profit_data]
        self.drawdown = self.calculate_drawdowns(self.winner_data)
        print("最大回撤：",max(self.drawdown))

        for i in range(0,8):
            A = i*0.01 + 0.03
            B = A - 0.03
            times = self.find_drawdown_events(self.drawdown, A, B)
            print("回撤%.2f进，%.2f出" % (A, B), len(times))
            print(times)

        """
        A = 0.03
        B = 0
        times = self.find_drawdown_events(self.drawdown, A,B)
        print("回撤%.2f进，%.2f出"%(A,B),len(times))
        print(times)
        A = 0.06
        B = 0.03
        times = self.find_drawdown_events(self.drawdown, A,B)
        print("回撤%.2f进，%.2f出"%(A,B),len(times))
        A = 0.08
        B = 0.06
        times = self.find_drawdown_events(self.drawdown, A,B)
        print("回撤%.2f进，%.2f出"%(A,B),len(times))
        A = 0.10
        B = 0.08
        times = self.find_drawdown_events(self.drawdown, A,B)
        print("回撤%.2f进，%.2f出"%(A,B),len(times))
        A = 0.11
        B = 0.10
        times = self.find_drawdown_events(self.drawdown, A,B)
        print("回撤%.2f进，%.2f出"%(A,B),len(times))
        A = 0.12
        B = 0.11
        times = self.find_drawdown_events(self.drawdown, A,B)
        print("回撤%.2f进，%.2f出"%(A,B),len(times)) """

    def calculate_drawdowns(self,equity_time_list):
        if not equity_time_list:
            return []

        # 初始化变量
        max_equity = 25000000  # 初始的最大权益是列表中的第一个权益
        max_drawdown = 0  # 历史最大回撤初始化为0
        drawdowns_time_list = []

        for equity, time in equity_time_list:
            # 计算当前回撤
            current_drawdown = (max_equity - equity) / max_equity if max_equity > 0 else 0

            # 更新历史最大回撤
            max_drawdown = max(max_drawdown, current_drawdown)

            # 如果当前权益高于历史最大权益，则更新历史最大权益
            if equity > max_equity:
                max_equity = equity
                max_drawdown = 0  # 重置最大回撤

            # 存储每个时间点的最大回撤、当前回撤和时间
            drawdowns_time_list.append((max_drawdown, current_drawdown, time))

        return drawdowns_time_list


obj = Test()
obj.get_data()
