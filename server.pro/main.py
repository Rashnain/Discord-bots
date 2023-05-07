from asyncio import sleep
from random import randint
from dotenv import dotenv_values

import discord
from discord import Option
from discord.enums import Status
from discord.ext import commands, tasks

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options


config = dotenv_values('.env')

bot = discord.Bot(owner_id=int(config['DISCORD_OWNER_ID']))


async def slow_type(element, text: str, delay: int | float = 0.0):
    for character in text:
        element.send_keys(character)
        if '-headless' not in options.arguments:
            await sleep(delay + randint(1, 2) / 10)


async def log(text: str, delay: float = .5):
    print(text)
    await sleep(delay)


def check(msg):
    return msg.author.id == bot.application_id and \
           (msg.content == 'We will see...' or msg.content == 'The captcha has expired.')


async def change_status(activity: str, status: Status):
    await bot.change_presence(activity=discord.Game(name=activity), status=status)


async def login():
    # Login
    driver.get('https://server.pro/login')
    await log('login page', .1)
    # Email
    email = driver.find_element(By.ID, 'input-email')
    await slow_type(email, config['SERVER_PRO_EMAIL'])
    email.send_keys(Keys.TAB)
    await log('email', .1)
    # Password
    pswd = driver.find_element(By.ID, 'input-password')
    await slow_type(pswd, config['SERVER_PRO_PWD'])
    await log('password', .1)
    # Validating
    driver.find_element(By.CSS_SELECTOR, 'button.button-primary').send_keys(Keys.SPACE)
    await log('validation')
    # Captcha
    if '-headless' not in options.arguments:
        input('captcha...')
    # Dark mode
    trigger = driver.find_element(By.CSS_SELECTOR, 'div.dropdown-trigger')
    ActionChains(driver).move_to_element(trigger).perform()
    await log('trigger', 2)
    driver.find_element(By.CSS_SELECTOR, 'span.switch-background').click()
    await log('dark mode')
    # Configuration/Resume Server
    button = driver.find_element(By.CSS_SELECTOR, 'button.button-primary')
    # Console / timer
    if button.get_attribute('innerHTML') == 'Control Panel':
        renew_check.start()
    else:
        # Change status
        await change_status('waiting for resume', Status.idle)
        check_integrity.start()


async def initialize():
    # Go to the console
    driver.get('https://server.pro/13479479/console')
    await log('console page')
    bot.consolable = True
    # Renew timer
    bot.timer = driver.find_element(By.CSS_SELECTOR, 'div.margin-tiny p.hint')
    # Renew button
    bot.renew_link = driver.find_element(By.CSS_SELECTOR, 'div.margin-tiny a.action')
    # Change status
    await change_status('Minecraft', Status.online)


# Manage captchas
async def captcha_loop(message: str):
    if 'resume' not in driver.current_url:
        bot.consolable = False
        bot.renew_link.click()

    bot.captcha_answer = ''
    expire_check.start()

    renewage = True
    while renewage:
        # Captcha capture
        if 'resume' in driver.current_url:
            captcha_img = driver.find_element(By.CSS_SELECTOR, 'div.col-md-9.mb-5 div img')
        else:
            captcha_img = driver.find_element(By.CSS_SELECTOR, 'div.modal div.content div img')
        captcha_img.screenshot('captcha.png')
        # Message choice
        if bot.captcha_answer != '':
            msg = 'Incorrect'
        else:
            msg = message
        # Send captcha
        if bot.captcha_msg:
            await bot.captcha_msg.edit(msg, file=discord.File('captcha.png'), attachments=[])
        else:
            bot.captcha_msg = await bot.channel.send(msg, file=discord.File('captcha.png'))

        captcha_input = driver.find_element(By.XPATH, '//div[@class="form-group-foot"]//input[@type="text"]')
        # Waiting for the message
        bot.captchable = True
        reponse = await bot.wait_for('message', check=check)
        bot.captchable = False
        # Check answer
        if reponse.content != 'The captcha has expired.':
            renewage = False
            await slow_type(captcha_input, bot.captcha_answer, 0.3)
            # Validation
            driver.find_element(By.CSS_SELECTOR, 'button.button-positive').click()
            await log('try captcha')
            # Check if it failed
            for img in driver.find_elements(By.TAG_NAME, 'img'):
                if img.get_attribute('src').startswith('https://server.pro/api/captcha/get?'):
                    driver.find_element(By.CSS_SELECTOR, 'div.alert.negative div.head div.subhead').click()
                    renewage = True
                    await log('captcha failed')

        else:  # Expiration
            bot.captcha_answer = ''
            if 'resume' in driver.current_url:
                driver.refresh()
                await log('expiration refresh')
            else:
                driver.find_element(By.CSS_SELECTOR, 'div.controls').click()
                bot.renew_link.click()
                await log('expiration')

        await log('deleting message')

        if renewage and await check_integrity() > 11:
            expire_check.cancel()
            await bot.captcha_msg.edit(content='Someone renewed with the website.', attachments=[])
            await sleep(5)
            await bot.captcha_msg.delete()
            bot.captcha_msg = None
            renew_check.restart()
            await log('someone renewed with website', 3)

        expire_check.restart()

    await bot.captcha_msg.edit(content=':thumbsup:', attachments=[])
    await log('valid captcha')
    expire_check.cancel()
    if 'console' in driver.current_url:
        bot.consolable = True
        console_input = driver.find_element(By.XPATH, '//input[@name="text"]')
        await slow_type(console_input, 'say Renewed')
        console_input.send_keys(Keys.RETURN)
    await sleep(5)
    await bot.captcha_msg.delete()
    bot.captcha_msg = None


@tasks.loop(minutes=10)
async def check_integrity():
    print('integrity')
    print(check_integrity.next_iteration)
    original_window = driver.current_window_handle
    # resume during "waiting for resume"
    if driver.current_url == 'https://server.pro/':
        driver.refresh()
        try:  # Queue or nothing
            button = driver.find_element(By.CSS_SELECTOR, 'button.button-primary')
        except NoSuchElementException:  # Transferring
            await log('transferring')
            if bot.is_resuming:
                check_integrity.cancel()
            return False
        if button.get_attribute('innerHTML') == 'Control Panel':  # Already resumed
            await log('already resumed')
            renew_check.start()
            await log('renew check')
            check_integrity.cancel()
            return None
        try:  # Queue
            driver.find_element(By.CSS_SELECTOR, 'p.percentage')
            await log('queue')
            if bot.is_resuming:
                check_integrity.cancel()
            return False
        except NoSuchElementException:  # Nothing
            await log('nothing')
            return True
    elif 'console' in driver.current_url:  # Renew during "renew_check"
        driver.switch_to.new_window('tab')
        driver.get('https://server.pro/13479479')
        await log('integrity now')
        timer = driver.find_element(By.CSS_SELECTOR, 'div.margin-tiny p.hint')
        unite = timer.get_attribute('innerHTML')[-2:]
        time_remaining = int(timer.get_attribute('innerHTML')[11:13].strip())
        if unite == 's.':
            time_remaining = 0
        driver.close()
        driver.switch_to.window(original_window)
        return time_remaining
    else:  # During a "resume" captcha
        return 0


# Check the remaining time
@tasks.loop()
async def renew_check():
    await initialize()
    remaining_time = int(bot.timer.get_attribute('innerHTML')[11:13].strip())
    print('renew_check', remaining_time)
    if remaining_time <= 11:
        print('renew_check now')
        try:
            await captcha_loop('Renew required, use /captcha to resolve it')
        except StaleElementReferenceException or NoSuchElementException:
            # Manages the closure of the service
            if driver.current_url == 'https://server.pro/':
                await log('service expiration')
                await change_status('waiting for resume', Status.idle)
                await bot.captcha_msg.edit('The server expired.\nDo `/resume` to resume it.',
                                           attachments=[])
                await log('removing last message')
                expire_check.cancel()
                check_integrity.start()
                renew_check.cancel()
    else:
        print('renew_check in', remaining_time - 11)
        renew_check.change_interval(minutes=remaining_time - 11)


# Check if the captcha has expired (1 minute)
@tasks.loop(seconds=55)
async def expire_check():
    print('expire_check')
    if bot.captchable:
        print('expire_check now')
        msg = await bot.channel.send('The captcha has expired.')
        await msg.delete()
    print('expire_check fin')


@bot.event
async def on_ready():
    print('Bot ready, logged as', bot.user)
    # Change status
    await change_status('booting', Status.dnd)
    # Channel where captcha ar sent to
    bot.channel = bot.get_channel(int(config['DISCORD_CAPTCHA_CHANNEL']))
    # Connection
    await login()


@bot.slash_command(description='Start the service')
async def resume(ctx):
    if driver.current_url == 'https://server.pro/' and not bot.is_resuming:
        msg = None
        bot.is_resuming = True
        integrity = await check_integrity()
        if integrity is True:
            check_integrity.cancel()
            driver.find_element(By.CSS_SELECTOR, 'button.button-primary').click()
            int_msg = await ctx.respond('Answer the captcha below using /captcha')
            bot.captcha_msg = await int_msg.original_response()
            # Captcha
            await captcha_loop('Answer the captcha below using /captcha')
        elif integrity is False:
            driver.get('https://server.pro/queue')
            await log('maybe transferring')
        else:
            return
        # If you are not allowed directly
        if 'queue' in driver.current_url:
            await log('queue')
            await change_status('in queue', Status.idle)
            # Displaying the place in the queue
            try:  # In case it is instantaneous
                queue = driver.find_element(By.CSS_SELECTOR, 'p.percentage')
                msg = await ctx.send(queue.get_attribute('innerHTML'))
                while True:
                    try:
                        await sleep(5)
                        await msg.edit(content=queue.get_attribute('innerHTML'))
                    except StaleElementReferenceException:
                        break
                await msg.edit(content='Position 0')
            except NoSuchElementException:
                pass
            # Start Server
            driver.find_element(By.CSS_SELECTOR, 'button.button-positive.mt-1').click()
        # Transferring
        await log('transferring', 2)
        driver.refresh()
        await log('refresh')
        transfer = driver.find_element(By.CSS_SELECTOR,
                                       'div.col-xl-7.col-lg-8.col-sm-6.col-6.mb-3.mb-lg-0 h4')
        if not msg:
            msg = await ctx.send(transfer.get_attribute('innerHTML'))
        else:
            await msg.edit(transfer.get_attribute('innerHTML'))
        while True:
            if transfer.get_attribute('innerHTML').startswith('Transferring'):
                await sleep(5)
                await msg.edit(content=transfer.get_attribute('innerHTML'))
            else:
                break
        await msg.edit(content="The server has started, it'll be ready in a minute.")
        await log('transferring finished')
        # Console / timer
        renew_check.start()
        bot.is_resuming = False
        await sleep(5)
        await msg.delete()
    else:
        await ctx.respond('The service is already resumed.', ephemeral=True)


@bot.slash_command(description='Answer to a captcha')
async def captcha(ctx, *, answer: Option(str, min_length=4, max_length=6)):
    if bot.captchable:
        bot.captcha_answer = answer
        msg = await ctx.respond('We will see...')
        await sleep(5)
        await msg.delete_original_response()
    else:
        await ctx.respond('Renew not required', ephemeral=True)


@bot.slash_command(description='Restart the server')
async def restart(ctx):
    if bot.consolable:
        driver.find_element(By.CSS_SELECTOR, 'div.button-power.restart').click()
        msg = await ctx.respond('Restarting...')
        await sleep(5)
        await msg.delete_original_response()
    else:
        await ctx.respond('Renewing underway.', ephemeral=True)


@bot.slash_command(description='Stop the server')
async def stop(ctx):
    if bot.consolable:
        driver.find_element(By.CSS_SELECTOR, 'div.button-power.power-off').click()
        msg = await ctx.respond('Stopping...')
        await sleep(5)
        await msg.delete_original_response()
    else:
        await ctx.respond('Renewing underway.', ephemeral=True)


@bot.slash_command(description='Start the server')
async def start(ctx):
    if bot.consolable:
        driver.find_element(By.CSS_SELECTOR, 'div.button-power.power-on').click()
        msg = await ctx.respond('Starting...')
        await sleep(5)
        await msg.delete_original_response()
    else:
        await ctx.respond('Renewing underway.', ephemeral=True)


@bot.slash_command(description='Send a command and/or return the 10 last output lines (owner only)')
@commands.is_owner()
async def console(ctx, command: Option(str, required=False)):
    if bot.consolable:
        if command:
            console_input = driver.find_element(By.XPATH, '//input[@name="text"]')
            await slow_type(console_input, command)
            console_input.send_keys(Keys.RETURN)
            await log('command')
        commandes = driver.find_elements(By.CSS_SELECTOR, 'div.lines p')
        results = ''
        for i in range(10, 0, -1):
            results += commandes[-i].text + '\n'
        await ctx.respond(results, ephemeral=True)
    else:
        await ctx.respond('Renewing underway.', ephemeral=True)


@bot.slash_command(description='Shutdown the bot (owner only)')
@commands.is_owner()
async def shutdown(ctx):
    await ctx.respond('Adios', ephemeral=True)
    await bot.close()


if __name__ == '__main__':
    # Variables
    bot.captcha_msg = None
    bot.captchable = False
    bot.is_resuming = False
    bot.timer = None
    bot.renew_link = None
    bot.consolable = False
    bot.channel = None
    # Driver
    options = Options()
    options.add_argument('-headless')
    driver = webdriver.Firefox(options=options)
    if '-headless' not in options.arguments:
        driver.set_window_position(0, 0)
        driver.set_window_size(950, 520)
    # Starting/stoping
    bot.run(config['DISCORD_BOT_TOKEN'])
    driver.quit()
