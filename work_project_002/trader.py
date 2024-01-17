from datetime import datetime, time
import backtrader as bt
from BackTraderQuik.QKStore import QKStore  # Хранилище QUIK


class MacdRsiStochStrategy(bt.Strategy):
    """Система с использованием индикаторов MACD, RSI, и Stochastic Oscillator
    для тестирования торговли на исторических данных."""
    # Задаем параметры стратегии
    params = (
        ('k_period', 15),  # период для линии %K (индикатор Stochastic Oscillator)
        ('d_period', 4),  # период для линии %D (индикатор Stochastic Oscillator)
        ('macd_2_1', 7),  # быстрая скользящая средняя (индикатор MACD)
        ('macd_2_2', 20),  # медленная скользящая средняя (индикатор MACD)
        ('macdsig_2_1', 9),  # сигнальная линия (индикатор MACD)
        ('rsiperiod', 12),  # индикатор RSI
    )
    def log(self, txt, dt=None):
        """Вывод строки с датой на консоль"""
        dt = bt.num2date(self.datas[0].datetime[0]) if not dt else dt  # Заданная дата или дата текущего бара
        print(f'{dt.strftime("%d.%m.%Y %H:%M")}, {txt}')  # Выводим дату и время с заданным текстом на консоль

    def __init__(self):
        """Инициализация торговой системы"""
        self.isLive = False  # Сначала будут приходить исторические данные, затем перейдем в режим реальной торговли
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


    def next(self):
        """Получение следующего исторического/нового бара"""
        for data in self.datas:  # Пробегаемся по всем запрошенным барам
            self.log(f'{data.p.dataname} Open={data.open[0]:.5f}, High={data.high[0]:.5f}, Low={data.low[0]:.5f}, '
                     f'Close={data.close[0]:.5f}, Volume={data.volume[0]:.2f}')

        if self.isLive:  # Если в режиме реальной торговли
            self.log(f'Свободные средства: {self.broker.getcash()}, Баланс: {self.broker.getvalue()}')
            self.log(f'Close={self.DataClose[0]:.5f}')

            position = self.getposition()

            # Если нет открытой позиции и есть сигнал на вход
            if not position:
                if (self.macd1.macd[0] < self.macd1.signal[0]
                    and self.macd1.signal[0] - self.macd1.macd[0] < self.macd1.signal[-1] - self.macd1.macd[-1]) \
                        or (self.macd1.macd[0] > self.macd1.signal[0]
                            and self.macd1.macd[0] - self.macd1.signal[0] > self.macd1.macd[-1] - self.macd1.signal[
                                -1]):

                    if self.crossover_up and self.rsi[0] >= 50:
                        self.log(f'Открытие покупки')
                        self.buy()  # Заявка на покупку по рыночной цене

                elif (self.macd1.macd[0] > self.macd1.signal[0]
                      and self.macd1.macd[0] - self.macd1.signal[0] < self.macd1.macd[-1] - self.macd1.signal[-1]) \
                        or (self.macd1.macd[0] < self.macd1.signal[0]
                            and self.macd1.signal[0] - self.macd1.macd[0] > self.macd1.signal[-1] - self.macd1.macd[
                                -1]):
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

    def notify_data(self, data, status, *args, **kwargs):
        """Изменение статуса приходящих баров"""
        data_status = data._getstatusname(status)  # Получаем статус (только при LiveBars=True)
        print(data_status)  # Не можем вывести в лог, т.к. первый статус DELAYED получаем до первого бара (и его даты)
        self.isLive = data_status == 'LIVE'  # Режим реальной торговли

    def notify_order(self, order):
        """Изменение статуса заявки"""
        if order.status in (bt.Order.Created, bt.Order.Submitted, bt.Order.Accepted):  # Если заявка создана,
            # отправлена брокеру, принята брокером (не исполнена)
            self.log(f'Alive Status: {order.getstatusname()}. TransId={order.ref}')
        elif order.status in (bt.Order.Canceled, bt.Order.Margin, bt.Order.Rejected, bt.Order.Expired):  # Если заявка
            # отменена, нет средств, заявка отклонена брокером, снята по времени (снята)
            self.log(f'Cancel Status: {order.getstatusname()}. TransId={order.ref}')
        elif order.status == bt.Order.Partial:  # Если заявка частично исполнена
            self.log(f'Part Status: {order.getstatusname()}. TransId={order.ref}')
        elif order.status == bt.Order.Completed:  # Если заявка полностью исполнена
            if order.isbuy():  # Заявка на покупку
                self.log(f'Bought @{order.executed.price:.5f}, Cost={order.executed.value:.5f}, Comm={order.executed.comm:.5f}')
            elif order.issell():  # Заявка на продажу
                self.log(f'Sold @{order.executed.price:.5f}, Cost={order.executed.value:.5f}, Comm={order.executed.comm:.5f}')

    def notify_trade(self, trade):
        """Изменение статуса позиции"""
        if trade.isclosed:  # Если позиция закрыта
            self.log(f'Trade Profit, Gross={trade.pnl:.5f}, NET={trade.pnlcomm:.5f}')


if __name__ == '__main__':  # Точка входа при запуске этого скрипта
    cerebro = bt.Cerebro(stdstats=False)  # Инициируем "движок" BackTrader. Стандартная статистика сделок и
    # кривой доходности не нужна

    clientCode = 'Код клиента'  # Код клиента (присваивается брокером)
    firmId = 'Код фирмы'  # Код фирмы (присваивается брокером)
    # symbol = 'TQBR.SBER'  # Тикер
    symbol = 'VBH4'  # Для фьючерсов: <Код тикера><Месяц экспирации: 3-H, 6-M, 9-U, 12-Z><Последняя цифра года>

    cerebro.addstrategy(MacdRsiStochStrategy)  # Добавляем торговую систему
    store = QKStore()  # Хранилище QUIK
    broker = store.getbroker(use_positions=False, ClientCode=clientCode, FirmId=firmId, TradeAccountId='L01-00000F00',
                             LimitKind=2, CurrencyCode='SUR', IsFutures=False)  # Брокер со счетом фондового рынка РФ
    # broker = store.getbroker(use_positions=False)  # Брокер со счетом по умолчанию (срочный рынок РФ)
    cerebro.setbroker(broker)  # Устанавливаем брокера
    data = store.getdata(dataname=symbol, timeframe=bt.TimeFrame.Minutes, compression=15,
                         fromdate=datetime(2023, 9, 5), sessionstart=time(7, 0), LiveBars=True)  # Исторические и
    # новые минутные бары за все время
    cerebro.adddata(data)  # Добавляем данные

    data1 = store.getdata(dataname=symbol, timeframe=bt.TimeFrame.Minutes, compression=240,
                         fromdate=datetime(2023, 9, 5), sessionstart=time(7, 0), LiveBars=True)  # Исторические и
    # новые минутные бары за все время
    cerebro.adddata(data1)

    cerebro.addsizer(bt.sizers.FixedSize, stake=100000)  # Кол-во акций для покупки/продажи
    cerebro.run()  # Запуск торговой системы
