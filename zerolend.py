import asyncio
import logging
from client import Client
from config import ZEROLEND_CONTRACTS, ZEROLEND_POOL, ERC20_ABI , TOKENS_PER_CHAIN
from functions import get_amount
from termcolor import colored

# Настройка логирования
file_log = logging.FileHandler('file.log', encoding='utf-8')
console_out = logging.StreamHandler()
logging.basicConfig(handlers=(file_log, console_out),
                    level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

class Zerolend:
    """
    Класс Zerolend для взаимодействия с контрактами Zerolend.

    Attributes:
        client (Client): Клиент для взаимодействия с блокчейном.
        token_contract: Контракт токена USDC.
        pool_contract: Основной контракт Zerolend.
    """

    def __init__(self, client: Client):
        """
        Инициализация класса Zerolend.

        Args:
            client (Client): Клиент для взаимодействия с блокчейном.
        """
        self.client = client
        # Получаем контракт USDC токена
        self.token_contract = self.client.get_contract(
            contract_address=ZEROLEND_CONTRACTS[self.client.chain_name]['USDC'], abi=ERC20_ABI
        )
        # Получаем основной контракт Zerolend
        self.pool_contract = self.client.get_contract(
            contract_address=ZEROLEND_CONTRACTS[self.client.chain_name]['pool'],
            abi=ZEROLEND_POOL,
        )

    async def supply(self, amount_in_wei: float):
        """
        Внесение средств в контракт Zerolend.

        Args:
            amount_in_wei (float): Сумма в wei для внесения в контракт.

        Returns:
            dict: Результат отправки транзакции.
        """
        # Выполнение одобрения (approve) токенов для контракта
        # await self.client.make_approve(
        #     TOKENS_PER_CHAIN[self.client.chain_name][self.client.chain_token], self.pool_contract.address, 2 ** 256 - 1
        # )
        # Создание транзакции для внесения средств
        transaction = await self.pool_contract.functions.supply(
            ZEROLEND_CONTRACTS[self.client.chain_name]['USDC'],
            amount_in_wei,
            self.client.address,
            0
        ).build_transaction(await self.client.prepare_tx())

        # Отправка транзакции
        return await self.client.send_transaction(transaction)

    async def winthdraw(self):
        """
        Вывод средств из контракта Zerolend.

        Returns:
            dict: Результат отправки транзакции.
        """
        # Получение баланса токенов на адресе клиента
        amount_in_wei = await self.token_contract.functions.balanceOf(self.client.address).call()
        # Создание транзакции для вывода средств
        transaction = await self.pool_contract.functions.withdraw(
            ZEROLEND_CONTRACTS[self.client.chain_name]['USDC'],
            amount_in_wei,
            self.client.address
        ).build_transaction(await self.client.prepare_tx())

        # Отправка транзакции
        return await self.client.send_transaction(transaction)

async def main():
    """
    Основная функция для взаимодействия с пользователем и контрактом Zerolend.
    """
    proxy = ''
    # Получение private_key от пользователя
    while True:
        try:
            private_key = input(colored("Введите private key: ", 'light_green'))
            w3_client = Client(private_key=private_key, proxy=proxy)
            break
        except Exception as er:
            logging.error(f"Некорректный private key! {er}")

    zero_client = Zerolend(client=w3_client)
    try:
        # Получение баланса USDC токенов
        balance = await zero_client.client.get_balance(TOKENS_PER_CHAIN['Linea']['USDC'])
    except Exception as er:
         logging.error(f"Ошибка при получении баланса: {er}")
         exit(1)

    # Преобразование баланса в wei
    amount_in_wei = get_amount(balance)
    logging.info("Пробуем аппрувить и положить в лендинг")
    try:
        # Попытка внесения средств в лендинг
        await zero_client.supply(amount_in_wei)
        logging.info("Удачно!")
    except Exception as er:
        logging.error(f"Ошибка при лендинге!")
        exit(1)

    # Вопрос пользователю о выводе средств
    response = input(colored("Вывести из пула?", 'light_green'))
    try:
        if response in "YyДд":
            logging.info(f"Выводим из пула USDC")
            # Попытка вывода средств
            await zero_client.winthdraw()
            logging.info("Удачно!")
        else:
            logging.info("Программа завершилась")
    except Exception as er:
        logging.info(f"Ошибка вывода из пула",)

# Запуск основной функции
asyncio.run(main())
