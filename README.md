# PVU bot
[ [Channel](https://t.me/Cum_Insider) ]

- [Установка под Windows](#Установка-под-Windows)
- [Установка под Ubuntu](#Установка-под-Ubuntu)
- [Работа со скриптом](#Работа-со-скриптом)
- [Получение токена авторизации](#О-токене-авторизации)
- [Логика работы скрипта](#Логика-работы)


## Установка под Windows
- Установите [Python 3.11](https://www.python.org/downloads/windows/). Не забудьте поставить галочку напротив "Add Python to PATH".
- Установите пакетный менеджер [Poetry](https://python-poetry.org/docs/): [инструкция](https://teletype.in/@alenkimov/poetry).
- Установите MSVC и Пакет SDK для Windows: [инструкция](https://teletype.in/@alenkimov/web3-installation-error). Без этого при попытке установить библиотеку web3 будет возникать ошибка "Microsoft Visual C++ 14.0 or greater is required".
- Установите [git](https://git-scm.com/download/win). Это позволит с легкостью получать обновления скрипта командой `git pull`
- Откройте консоль в удобном месте.
  - Склонируйте (скачайте) этот репозиторий:
    ```bash
    git clone https://github.com/AlenKimov/pvu.git
    ```
  - Перейдите в папку проекта:
    ```bash
    cd pvu
    ```
  - Установите требуемые библиотеки:
    ```bash
    poetry update
    ```

## Установка под Ubuntu
- Обновите систему:
```bash
sudo apt update && sudo apt upgrade -y
```
- Установите [git](https://git-scm.com/download/linux) и screen:
```bash
sudo apt install screen git -y
```
- Установите Python 3.11 и зависимости для библиотеки web3:
```bash
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt install python3.11 python3.11-dev build-essential libssl-dev libffi-dev -y
ln -s /usr/bin/python3.11/usr/bin/python
```
- Установите [Poetry](https://python-poetry.org/docs/):
```bash
curl -sSL https://install.python-poetry.org | python -
export PATH="/root/.local/bin:$PATH"
```
- Склонируйте этот репозиторий, после чего перейдите в него:
```bash
git clone https://github.com/AlenKimov/pvu.git
cd pvu
```
- Установите требуемые библиотеки командой `poetry update`.

## Работа со скриптом
Для запуска скрипта пропишите следующую команду (или запустите `start.bat` на Windows):
```bash
poetry run python start.py
```

После первого запуска создадутся файлы `private_keys.txt` и `tokens.txt` в папке `input`.

Для доступа к аккаунту PVU боту требуется токен авторизации.

Токен авторизации можно либо [достать самому](#О-токене-авторизации) и внести в файл `tokens.txt`, 
либо его автоматически будет создавать бот. Для последнего нужно внести приватный ключ (не сид-фраза)
в файл `private_keys.txt`.

Некоторые параметры бота можно изменить в файле `bot/config.py`.


## О токене авторизации
Получить токен авторизации можно следующим способом:
1. Авторизуемся с нашим кошельком на сайте PVU.
2. Заходим в инструменты разработчика, вкладка **Сеть** (**Network**) [**Ctrl + Shift + I**].
4. Выбираем фильтр **Fetch/XHR**.
5. Обновляем страницу [**Ctrl + R**].
6. Находим запрос `userinfo` (можно другой) и в **заголовках запроса** (**Headers**) копируем значение поля `Authorization`:
![me/ -> headers -> authorization](images/where-is-my-token.png)


## Логика работы
- Каждые 300 секунд (настраивается в `bot/config.py`) скрипт запрашивает список земель и их слотов (растений).
- После он подсчитывает количество ворон и требующих полива растений и вычисляет, сколько ему нужно купить инструментов опираясь на количество уже имеющихся инструментов и LE.
- После этого он поливает растения, отгоняет ворон и собирает награды.
