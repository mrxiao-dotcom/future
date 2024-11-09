import json
import numpy as np
import pyqtgraph as pg
import time
import datetime
import sys
from PyQt5.Qt import *
from PyQt5 import QtCore
from main_frame import Ui_MainWindow
from pop_win_choose import Ui_Form
from PyQt5.QtChart import QChart, QValueAxis, QChartView, QSplineSeries
from comm.dbConnecterTB import MyDBConn
from comm import commFunctions as cf

class Window(QMainWindow, Ui_MainWindow):
    def __init__(self, app):
        super(QMainWindow, self).__init__()
        self.app = app
        self.profit_data = ProfitData() #初始化数据
        self.setup_ui()  # 渲染画布
        self.update_data_thread = UpdateDataThread()  # 创建更新波形数据线程
        self.connect_signals()  # 绑定触发事件
        self.stratage_init()
        self.last_job_time = datetime.datetime.now()



    def setup_ui(self):
        self.setupUi(self)

        # 加载波形
        self.set_graph_ui()  # 设置绘图窗口
        self.data_list = []
        self.time_list = []
        #self.profit_target = []
        self.plot_show(self.time_list,self.data_list)
        self.plot_show_mini(self.time_list, self.data_list)

        #最后N个，设定小图窗口的大小
        self.N = 1000


    def set_graph_ui(self):
        # pg.setConfigOption('background', 'w')
        pg.setConfigOptions(antialias=True, background='w')  # pyqtgraph全局变量设置函数，antialias=True开启曲线抗锯齿
        win1 = pg.GraphicsLayoutWidget()  # 创建pg layout，可实现数据界面布局自动管理
        win2 = pg.GraphicsLayoutWidget()  # 创建pg layout，可实现数据界面布局自动管理
        win3 = pg.GraphicsLayoutWidget()  # 创建pg layout，可实现数据界面布局自动管理

        #date_axis = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')

        # pg绘图窗口可以作为一个widget添加到GUI中的graph_layout，当然也可以添加到Qt其他所有的容器中
        self.plot_view.addWidget(win1)
        self.dym_plot_view = win1.addPlot(title="全局走势",axisItems = {'bottom': pg.DateAxisItem()})  # 添加第一个绘图窗口
        self.dym_plot_view.setLabel('left', text='权益', color='#000000')  # y轴设置函数
        self.dym_plot_view.showGrid(x=True, y=True)  # 栅格设置函数
        self.dym_plot_view.setLogMode(x=False, y=False)  # False代表线性坐标轴，True代表对数坐标轴
        self.dym_plot_view.setLabel('bottom', text='时间', units='s')  # x轴设置函数

        self.plot_view_mini.addWidget(win2)
        self.dym_plot_view_mini = win2.addPlot(title="局部走势", axisItems={'bottom': pg.DateAxisItem()})  # 添加第一个绘图窗口
        self.dym_plot_view_mini.setLabel('left', text='权益', color='#000000')  # y轴设置函数
        self.dym_plot_view_mini.showGrid(x=True, y=True)  # 栅格设置函数
        self.dym_plot_view_mini.setLogMode(x=False, y=False)  # False代表线性坐标轴，True代表对数坐标轴
        self.dym_plot_view_mini.setLabel('bottom', text='时间', units='s')  # x轴设置函数

        self.plot_view_profit.addWidget(win3)
        self.dym_plot_view_profit = win3.addPlot(title="权益走势", axisItems={'bottom': pg.DateAxisItem()})  # 添加第一个绘图窗口
        self.dym_plot_view_profit.setLabel('left', text='权益', color='#000000')  # y轴设置函数
        self.dym_plot_view_profit.showGrid(x=True, y=True)  # 栅格设置函数
        self.dym_plot_view_profit.setLogMode(x=False, y=False)  # False代表线性坐标轴，True代表对数坐标轴
        self.dym_plot_view_profit.setLabel('bottom', text='时间', units='s')  # x轴设置函数


        y_max = max(self.profit_data.index_data) * 1.1
        self.dym_plot_view.setLimits(yMin=0, yMax=y_max)
        self.dym_plot_view_mini.setLimits(yMin=0, yMax=y_max)
        #self.dym_plot_view_profit.setLimits(yMin=5000000, yMax=12000000)
        # ax = self.dym_plot_view.getAxis('bottom')  # 设置x轴间隔
        # dx = [(value, str(value)) for value in range(128)]
        # ax.setTicks([dx, []])
        self.btn_buy.setEnabled(False)#初始化，屏蔽下单按钮
        self.btn_pause.setEnabled(False)
        self.le_buy_money.setText(self.le_single_money.text())

    def stratage_init(self):
        self.init_money = float(self.le_init_money.text())
        self.sys_money = 25000000
        self.holding_money = [0 for x in range(self.profit_data.get_len())]    #持仓份额
        self.profit = [0 for x in range(self.profit_data.get_len())]    #权益记录

    def plot_show(self,xdata=[],ydata=[]):
        # 显示波形
        #print(self.x_range)
        #print(np.append(self.x_range, np.max(self.x_range)+1))
        if len(xdata)>0:
            self.lb_time.setText(xdata[-1].strftime("%Y-%m-%d %H:%M:%S"))
        if len(ydata)>0:
            self.lb_max_drawdown.setText(str(ydata[-1]))
        xdata = [int(time.mktime(x.timetuple())) for x in xdata]
        #print(xdata)
        self.dym_plot_view.plot(xdata, ydata, pen='b', name='整体走势', clear=True)  # pen画笔颜色为蓝色


    def plot_show_mini(self,xdata=[],ydata=[]):
        # 显示波形
        #print(self.x_range)
        #print(np.append(self.x_range, np.max(self.x_range)+1))
        xdata = [int(time.mktime(x.timetuple())) for x in xdata]
        #print(xdata)
        self.dym_plot_view_mini.plot(xdata, ydata, pen='b', name='局部走势', clear=True)  # pen画笔颜色为蓝色

    def plot_show_profit(self,xdata=[],ydata=[]):
        # 显示波形
        #print(self.x_range)
        #print(np.append(self.x_range, np.max(self.x_range)+1))
        xdata = [int(time.mktime(x.timetuple())) for x in xdata]
        #print(xdata)
        self.dym_plot_view_profit.plot(xdata, ydata, pen='b', name='局部走势')  # pen画笔颜色为蓝色
        #zdata = [x*1.12 for x in ydata]
        #self.dym_plot_view_profit.plot(xdata, zdata, pen='r', name='局部走势2')  # pen画笔颜色为蓝色

    def connect_signals(self):
        # 绑定触发事件
        self.btn_start.clicked.connect(self.btn_start_clicked)
        self.btn_pause.clicked.connect(self.btn_pause_clicked)
        self.btn_fast.clicked.connect(self.btn_fast_clicked)
        self.btn_slow.clicked.connect(self.btn_slow_clicked)
        self.btn_quit.clicked.connect(self.btn_quit_clicked)
        self.btn_plus_one.clicked.connect(self.btn_plus_one_clicked)
        self.btn_minus_one.clicked.connect(self.btn_minus_one_clicked)
        self.btn_buy.clicked.connect(self.btn_buy_clicked)
        self.btn_clear.clicked.connect(self.btn_clear_clicked)
        self.btn_init_tim.clicked.connect(self.btn_init_tim_clicked)
        self.btn_profit_tim.clicked.connect(self.btn_profit_tim_clicked)
        self.btn_sell.clicked.connect(self.btn_sell_clicked)
        self.btn_choose.clicked.connect(self.btn_choose_clicked)
        self.btn_date_fromto.clicked.connect(self.btn_date_fromto_clicked)

        self.update_data_thread._signal_update.connect(self.update_data_thread_slot)  # 绑定回调事件

        #快捷键
        QShortcut(QKeySequence(self.tr(" ")), self, self.keypress_blank)
        QShortcut(QKeySequence(self.tr("B")), self, self.btn_buy_clicked)
        QShortcut(QKeySequence(self.tr("X")), self, self.btn_clear_clicked)
        QShortcut(QKeySequence(self.tr("left")), self, self.btn_slow_clicked)
        QShortcut(QKeySequence(self.tr("right")), self, self.btn_fast_clicked)

    def btn_start_clicked(self):
        # 开启按钮
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_buy.setEnabled(False)

        self.update_data_thread.is_exit = False
        self.update_data_thread.start()

    def keypress_blank(self):
        if self.btn_pause.isEnabled() and not self.btn_start.isEnabled():
            self.btn_pause_clicked()

        elif not self.btn_pause.isEnabled() and self.btn_start.isEnabled():
            self.btn_start_clicked()

#按钮功能区
    def btn_date_fromto_clicked(self):
        print(self.de_from,self.de_to)
        self.data_from = self.de_from.date().toPyDate()
        self.data_to = self.de_to.date().toPyDate()
        print(self.data_from,self.data_to)


    def btn_pause_clicked(self):
        #暂停按钮
        self.btn_pause.setEnabled(False)
        self.btn_start.setEnabled(True)
        self.update_data_thread.stop()
        self.btn_buy.setEnabled(True)

    def btn_quit_clicked(self):
        # 开启按钮
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(True)
        self.update_data_thread.reset()

    def btn_fast_clicked(self):
        #暂停按钮
        self.update_data_thread.sleep_time *= 0.8
        if self.update_data_thread.sleep_time< 0.01:
            self.update_data_thread.sleep_time = 0.01
        self.lb_speed.setText("{:.2f}".format(self.update_data_thread.sleep_time))

    def btn_slow_clicked(self):
        #暂停按钮
        self.update_data_thread.sleep_time *= 1.2
        if self.update_data_thread.sleep_time > 1.5:
            self.update_data_thread.sleep_time = 1.5
        self.lb_speed.setText("{:.2f}".format(self.update_data_thread.sleep_time))

    def btn_one_clicked(self):
        self.le_buy_money.setText(self.le_single_money.text())


    def btn_plus_one_clicked(self):
        old_money = float(self.le_buy_money.text())
        add_money = float(self.le_single_money.text())
        self.le_buy_money.setText(str(add_money+old_money))


    def btn_minus_one_clicked(self):
        old_money = float(self.le_buy_money.text())
        minus_money = float(self.le_single_money.text())
        if old_money - minus_money < 0:
            self.le_buy_money.setText(old_money)
        else:
            self.le_buy_money.setText(str(old_money - minus_money))

    def btn_buy_clicked(self):
        money = float(self.le_buy_money.text())
        if money>0 and self.x_range >0:
            self.holding_money[self.x_range] = money + self.holding_money[self.x_range-1]
            self.lb_holding_money.setText(str(self.holding_money[self.x_range]))
            self.btn_clear.setEnabled(True)

        self.lb_level_rate.setText("{:.2f}".format(float(self.lb_holding_money.text()) / self.profit[self.x_range]))
        self.lb_target_rate.setText("{:.2f}".format(float(self.lb_current_rate.text()) + float(self.lb_level_rate.text())*0.06))
        str_out_line = self.lb_time.text() + ", 买入资金："+self.le_buy_money.text() + ", 合计持仓：" + self.lb_holding_money.text()
        self.te_output.append(str_out_line)

    def btn_sell_clicked(self):
        money = float(self.le_buy_money.text())
        if self.holding_money[self.x_range-1] - money>0 and self.x_range >0:
            self.holding_money[self.x_range] = self.holding_money[self.x_range-1] - money
            self.lb_holding_money.setText(str(self.holding_money[self.x_range]))
        else:
            self.holding_money[self.x_range] = 0
            self.lb_holding_money.setText(str(self.holding_money[self.x_range]))

        str_out_line = self.lb_time.text() + ", 卖出资金："+self.le_buy_money.text() + ", 合计持仓：" + self.lb_holding_money.text()
        self.te_output.append(str_out_line)

    def btn_clear_clicked(self):
        if self.holding_money[self.x_range] > 0:
            self.holding_money[self.x_range] = 0
            self.lb_holding_money.setText(str(self.holding_money[self.x_range]))
            self.btn_clear.setEnabled(False)
        else:
            print("没有可平仓位")

        str_out_line = self.lb_time.text() + ", 清仓"
        self.te_output.append(str_out_line)

    def btn_init_tim_clicked(self):
        self.le_single_money.setText(str(self.init_money*0.5))


    def btn_profit_tim_clicked(self):
        self.le_single_money.setText(str(float(self.lb_profit.text())*0.5))

    def get_data(self, parameter):
        # print('This is a test.')
        #print(parameter)
        self.lb_data_source.setText(parameter)

    def btn_choose_clicked(self):
        self.wind_choose = ChildWindowChoose()
        self.wind_choose.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.WindowMaximizeButtonHint)
        #self.wind_choose.setParent(self)
        self.wind_choose.setWindowModality(Qt.WindowModal)
        self.wind_choose.show()
        self.wind_choose._signal.connect(self.get_data)


#信号槽
    def update_data_thread_slot(self, data):
        # 线程回调函数
        data = json.loads(data)

        self.x_range = data['x_range']
        need_draw = False

        if (datetime.datetime.now() - self.last_job_time).microseconds > 500000:
            self.last_job_time = datetime.datetime.now()
            need_draw = True

        #self.profit_target[self.x_range] = float(self.lb_target_rate.text())

        x_data = self.profit_data.get_time(self.x_range)
        y_data = self.profit_data.get_data(self.x_range)
        if need_draw:
            self.plot_show(x_data,y_data)

        x_data_mini = x_data[-self.N:]
        y_data_mini = y_data[-self.N:]

        if need_draw:
            self.plot_show_mini(x_data_mini,y_data_mini)

        y_data_profit = self.profit[:self.x_range]
        x_data = x_data[0:self.x_range]

        if need_draw:
            self.plot_show_profit(x_data,y_data_profit)


        draw_down = cf.MaxDrawdown(y_data_mini)
        if draw_down!=0:
            self.lb_drawback_rate.setText(str(draw_down[3]))
            self.lb_drawback_time.setText(str(draw_down[2]))


        #计算一下最新的权益

        i = self.x_range
        if i>0:
            #print(i, i - 1)
            #print("y_data",y_data[0:10])
            a = self.holding_money[i-1]
            #print(y_data)
            b = (y_data[i]-y_data[i-1])/y_data[i-1]

            ret = a*b
            self.profit[i] = ret + self.profit[i-1]

            #print(self.profit[0:10])
        else:
            #print(self.profit)
            self.profit[i] = self.init_money

        self.holding_money[i] = self.holding_money[i-1]

        self.lb_profit.setText("{:.2f}".format(self.profit[i]))
        #"{:.2f}".format(x)
        self.lb_holding_money.setText(str(self.holding_money[i]))
        self.lb_profit_rate.setText("{:.2f}".format(self.profit[i]/self.init_money))
        self.lb_current_rate.setText("{:.2f}".format(self.profit[i]/self.init_money))
        self.lb_avalid_money.setText("{:.2f}".format(self.profit[i]-self.holding_money[i]))
        self.lb_level_rate.setText("{:.2f}".format(float(self.lb_holding_money.text())/self.profit[i]))


class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.strftime("%Y-%m-%d %H:%M:%S")
        else:
            return json.JSONEncoder.default(self, obj)


# 使用线程不断更新波形数据
class UpdateDataThread(QThread):
    _signal_update = pyqtSignal(str)  # 信号

    def __init__(self, parent=None):
        super(UpdateDataThread, self).__init__(parent)
        self.qmut = QMutex()
        self.is_exit = False
        self.x_range = 0
        self.sleep_time = 0.5
        self.dc = MyDBConn(2)

    def run(self):
        while True:
            #self.qmut.lock()
            if self.is_exit:
                break
            #self.qmut.unlock()


            #print(self.x_data)
            dumps_data = {'x_range': self.x_range}
            self._signal_update.emit(json.dumps(dumps_data))  # 发送信号给槽函数
            self.x_range += 1

            time.sleep(self.sleep_time)

        #self.qmut.unlock()

    def stop(self):
        self.is_exit = True

    def reset(self):
        self.is_exit = True
        self.x_range = 0

class ChildWindowChoose(QWidget,Ui_Form):
    _signal = QtCore.pyqtSignal(str)
    def __init__(self):
        super(QWidget, self).__init__()
        # 引入子窗口类

        self.setupUi(self)
        self.InitListView()
        self.connect_signals()


    def InitListView(self):
        listModel = QStringListModel()
        self.list = ["CTA行情2008-最新", "沪深300行情（暂未更新）", "中证500行情（暂未更新）"]
        listModel.setStringList(self.list)
        self.lv_profit_list.setModel(listModel)
        self.data_str = ""


    def connect_signals(self):
        # 绑定触发事件
        self.btn_close.clicked.connect(self.btn_close_clicked)
        self.btn_choose.clicked.connect(self.btn_choose_clicked)
        self.lv_profit_list.clicked.connect(self.lv_profit_list_clicked)
    #
    def btn_close_clicked(self):
        if self.data_str == "":
            QMessageBox.information(self, "QListView", "必须选择一个数据")
            return
        self.close()

    def btn_choose_clicked(self):

        # 发送信号
        self._signal.emit(self.data_str)
        self.close()

    def lv_profit_list_clicked(self,item):
        if item.row() != 0:
            QMessageBox.information(self, "QListView", "您选择了：" + self.list[item.row()] + "当前系统，尚未更新，请重新选择")
            self.data_str = self.list[0]
            self.btn_choose.setEnabled(False)
        else:
            QMessageBox.information(self, "QListView", "您选择了：" + self.list[item.row()])
            self.data_str = self.list[item.row()]
            self.btn_choose.setEnabled(True)


class ProfitData():
    # 创建一个正弦波数据
    def __init__(self):
        self.dc = MyDBConn(2)
        ret = self.dc.QueryProfit()
        self.index_data = [x[0] for x in ret]
        self.time_data = [x[4] for x in ret]
        #self.index_data = [x[0] for x in ret][::-1]
        #self.time_data = [x[4] for x in ret][::-1]
        #print(self.index_data)


    def get_data(self,i): #返回data的前i的序列
        if i> len(self.index_data):
            i = len(self.index_data)

        return self.index_data[0:i+1]

    def get_time(self,i): #返回data的前i的序列
        if i> len(self.time_data):
            i = len(self.time_data)

        return self.time_data[0:i+1]

    def get_len(self):
        return len(self.index_data)

def main():
    app = QApplication(sys.argv)
    mywindow = Window(app)
    mywindow.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
