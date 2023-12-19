import backtrader as bt
from datetime import datetime


# Определяем класс стратегии
class MacdRsiStochStrategy(bt.Strategy):
    """Система с использованием индикаторов MACD, RSI, и Stochastic Oscillator
    для тестирования торговли на исторических данных."""
    # Задаем параметры стратегии
    params = (
        ('k_period', 14),  # период для линии %K (индикатор Stochastic Oscillator)
        ('d_period', 3),  # период для линии %D (индикатор Stochastic Oscillator)
        ('macd_2_1', 7),  # быстрая скользящая средняя (индикатор MACD)
        ('macd_2_2', 20),  # медленная скользящая средняя (индикатор MACD)
        ('macdsig_2_1', 9),  # сигнальная линия (индикатор MACD)
        ('rsiperiod', 14),  # индикатор RSI
    )

    def log(self, txt, dt=None):
        """Вывод строки с датой на консоль"""
        dt = bt.num2date(
            self.datas[0].datetime[0]) if not dt else dt  # Заданная дата или дата последнего бара первого тикера ТС
        print(f'{dt.strftime("%d.%m.%Y %H:%M")},  {txt}')  # Выводим дату и время с заданным текстом на консоль

    def __init__(self):
        """Инициализация торговой системы"""
        self.DataClose = self.datas[0].close  # значение закрытия бара
        self.Order = None  # Заявка
        self.BarExecuted = None  # Номер бара, на котором была исполнена заявка

        # инициализируем индикатор стохастик
        self.stoch = bt.indicators.Stochastic(self.data, period=self.p.k_period, period_dfast=self.p.d_period)

        # инициализируем сигналы пересечения
        self.crossover_up = bt.indicators.CrossUp(self.stoch.percK, self.stoch.percD)
        self.crossover_down = bt.indicators.CrossDown(self.stoch.percK, self.stoch.percD)

        # инициализируем индикатор MACD
        self.macd1 = bt.indicators.MACD(self.data1,
                                        period_me1=self.p.macd_2_1,
                                        period_me2=self.p.macd_2_2,
                                        period_signal=self.p.macdsig_2_1)

        # инициализируем индикатор RSI
        self.rsi = bt.indicators.RSI(self.data, period=self.p.rsiperiod)

    def notify_order(self, order):
        """Изменение статуса заявки"""
        if order.status in [order.Submitted,
                            order.Accepted]:  # Если заявка не исполнена (отправлена брокеру или принята брокером)
            return  # то статус заявки не изменился, выходим, дальше не продолжаем

        if order.status in [order.Completed]:  # Если заявка исполнена
            if order.isbuy():  # Заявка на покупку
                self.log(
                    f'Bought @{order.executed.price:.2f}, Cost={order.executed.value:.2f}, Comm={order.executed.comm:.2f}')
            elif order.issell():  # Заявка на продажу
                self.log(
                    f'Sold @{order.executed.price:.2f}, Cost={order.executed.value:.2f}, Comm={order.executed.comm:.2f}')
            self.BarExecuted = len(self)  # Номер бара, на котором была исполнена заявка
        elif order.status in [order.Canceled, order.Margin,
                              order.Rejected]:  # Заявка отменена, нет средств, отклонена брокером
            self.log('Canceled/Margin/Rejected')
        self.Order = None  # Этой заявки больше нет

    def notify_trade(self, trade):
        """Изменение статуса позиции"""
        if not trade.isclosed:  # Если позиция не закрыта
            return  # то статус позиции не изменился, выходим, дальше не продолжаем

        self.log(f'Trade Profit, Gross={trade.pnl:.2f}, NET={trade.pnlcomm:.2f}')

    def next(self):
        """Получение следующего бара"""
        self.log(f'Close={self.DataClose[0]:.2f}')

        position = self.getposition()

        # Если нет открытой позиции и есть сигнал на вход
        if not position:
            if (self.macd1.macd[0] < self.macd1.signal[0]
                and self.macd1.signal[0] - self.macd1.macd[0] < self.macd1.signal[-1] - self.macd1.macd[-1]) \
                    or (self.macd1.macd[0] > self.macd1.signal[0]
                        and self.macd1.macd[0] - self.macd1.signal[0] > self.macd1.macd[-1] - self.macd1.signal[-1]):

                if self.crossover_up and self.rsi[0] >= 50:
                    self.log(f'Открытие покупки')
                    self.buy()  # Заявка на покупку по рыночной цене

            elif (self.macd1.macd[0] > self.macd1.signal[0]
                  and self.macd1.macd[0] - self.macd1.signal[0] < self.macd1.macd[-1] - self.macd1.signal[-1]) \
                    or (self.macd1.macd[0] < self.macd1.signal[0]
                        and self.macd1.signal[0] - self.macd1.macd[0] > self.macd1.signal[-1] - self.macd1.macd[-1]):
                if self.crossover_down and self.rsi[0] <= 50:
                    self.log(f'Открытие продажи')
                    self.sell()  # Заявка на продажу по рыночной цене

        if position.size > 0:
            if self.crossover_down and self.rsi[0] <= 50:
                self.log(f'Закрытие покупки')
                # закрываем покупку
                self.close()

        if position.size < 0:
            if self.crossover_up and self.rsi[0] >= 50:
                self.log(f'Закрытие продажи')
                # закрываем продажу
                self.close()


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    cerebro = bt.Cerebro()  # Инициируем "движок" BackTrader
    cerebro.optstrategy(MacdRsiStochStrategy, k_period=range(10, 20),
                        d_period=range(3, 10))  # Торговая система на оптимизацию с параметрами.
                                                    # Первое значение входит, последнее - нет

    data = bt.feeds.GenericCSVData(
        dataname='Data\\SPBFUT.VBZ3_M15.txt',  # Файл для импорта
        separator='\t',  # Колонки разделены табуляцией
        dtformat='%d.%m.%Y %H:%M',  # Формат даты/времени DD.MM.YYYY HH:MI
        openinterest=-1,  # Открытого интереса в файле нет
        fromdate=datetime(2023, 9, 15),  # Начальная дата приема исторических данных (Входит)
        todate=datetime(2023, 11, 14),  # Конечная дата приема исторических данных (Не входит)
        timeframe=bt.TimeFrame.Minutes,
        compression=1)
    cerebro.adddata(data)  # Привязываем исторические данные
    cerebro.resampledata(data, timeframe=bt.TimeFrame.Minutes, compression=240)

    cerebro.broker.setcash(1000000)  # Стартовый капитал для "бумажной" торговли
    cerebro.addsizer(bt.sizers.FixedSize, stake=10)  # Кол-во акций для покупки/продажи
    cerebro.broker.setcommission(commission=0.00035)  # Комиссия брокера 0.1% от суммы каждой исполненной заявки
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='TradeAnalyzer')  # Привязываем анализатор закрытых сделок
    print('Прибыль/убытки по счету:')
    results = cerebro.run(maxcpus=8)  # Запуск торговой системы. Получение статистики.
    # Можно указать кол-во ядер процессора, которые будут загружены. Например, maxcpus=2
    print('Прибыль/убытки по закрытым сделкам:')
    stats = {}  # Статистику будем вести в виде словаря
    for result in results:  # Пробегаемся по статистике по всем параметрам
        p = (result[0].p.k_period, result[0].p.d_period)  # Параметр
        analysis = result[0].analyzers.TradeAnalyzer.get_analysis()  # Получаем данные анализатора закрытых сделок
        v = analysis['pnl']['net']['total']  # Прибыль/убытки по закрытым сделкам
        stats[p] = v  # Заносим статистику в словарь
        print(f'stoch({p}), {v:.2f}')
    bestStat = max(stats.items(), key=lambda x: x[1])  # Для получения лучшего/худшего значений в словаре переводим их
    worstStat = min(stats.items(), key=lambda x: x[1])  # в список кортежей, сравниваем 2-ой элемент (значения)
    avgStat = sum(stats.values()) / len(stats.values())  # Среднее значение как сумма значений разделенная на их кол-во
    print(f'Лучшие значения: stoch({bestStat[0]}), {bestStat[1]:.2f}')
    print(f'Худшие значени: stoch({worstStat[0]}), {worstStat[1]:.2f}')
    print(f'Среднее значение: {avgStat:.2f}')
