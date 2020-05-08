import discord
import base64

# selenium requires installation of https://github.com/mozilla/geckodriver/releases and add path/to/executable to $PATH
import selenium
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.chrome.options import Options

from PIL import Image
from io import BytesIO
import time
from typing import Optional
from config import PREFIX

BASE_DIR = '/home/thijs/Lichess-discord-bot'
answers = []
follow_ups = []
_puzzle_id = None


async def show_puzzle(message: discord.message.Message, puzzle_id: Optional[str] = '') -> None:
    # Create a headless instance of a web browser
    options = Options()
    options.headless = True
    driver = webdriver.Chrome(options=options)

    try:
        # Get a puzzle image
        driver.get(f'https://lichess.org/training/{puzzle_id}')

        if puzzle_id == '':
            puzzle_id = driver.current_url.split('/')[-1]
        global _puzzle_id
        _puzzle_id = puzzle_id

        board = driver.find_element_by_class_name('puzzle__board')
        time.sleep(.8)  # wait for the last move to play out
        im = Image.open(BytesIO(base64.b64decode(board.screenshot_as_base64)))  # take screenshot of page

        im.save(f'{BASE_DIR}/media/puzzle.png')

        embed = discord.Embed(title=f"Solve this! (puzzle {puzzle_id})",
                              url=f'https://lichess.org/training/{puzzle_id}',
                              colour=0x00ffff
                              )

        puzzle = discord.File(f'{BASE_DIR}/media/puzzle.png', filename="puzzle.png")
        embed.set_image(url="attachment://puzzle.png")
        embed.add_field(name="Answer with !answer", value="Use the standard algebraic notation, e.g. Qxb7+")

        await message.channel.send(file=puzzle, embed=embed)

        # Get answers
        WebDriverWait(driver, 10).until(
            ec.element_to_be_clickable((By.XPATH, "/html/body/div/main/div[2]/div[3]/div[2]/a"))).click()

        moves = driver.find_elements_by_tag_name('move')  # List of all "move" elements

        for i in range(len(moves)):  # Find the moves from where the user plays
            if 'good' in moves[i].get_attribute('class'):
                moves = moves[i:]
                break

        global answers, follow_ups  # update global variables
        answers = [move.text.split()[0] for move in moves[::2]]  # list of user-given answers
        if len(moves) > 1:
            follow_ups = [move.text.split()[0] for move in moves[1::2]]  # list of computer follow ups

        driver.quit()  # quit the connection
    except selenium.common.exceptions.NoSuchElementException:
        await message.channel.send(f"I can't find a puzzle with puzzle id '{puzzle_id}'")
        driver.quit()
        return


async def answer_puzzle(message: discord.message.Message, answer: str) -> None:
    embed = discord.Embed(title=f"Answering puzzle {_puzzle_id}",
                          url=f'https://lichess.org/training/{_puzzle_id}',
                          colour=0x00ffff
                          )
    if len(answers) == 0:
        embed.add_field(name="Oops!",
                        value="I'm sorry. I currently don't have the answers to a puzzle. Please try another "
                              f"{PREFIX}puzzle")
    elif answer.lower() == answers[0].lower():
        if len(follow_ups) == 0:
            embed.add_field(name="Correct!", value=f"Yes! The best move was {answers[0]}. You completed the puzzle!")
        else:
            embed.add_field(name="Correct!", value=f"Yes! The best move was {answers[0]}. The opponent responded with "
                                                   f"{follow_ups.pop(0)}, now what's the best move?")
        answers.pop(0)
    else:
        embed.add_field(name="Wrong!", value=f"Try again using {PREFIX}answer or get the answer with {PREFIX}bestmove")

    await message.channel.send(embed=embed)


async def give_best_move(message: discord.message.Message) -> None:
    embed = discord.Embed(title=f"Answering puzzle {_puzzle_id}",
                          url=f'https://lichess.org/training/{_puzzle_id}',
                          colour=0x00ffff
                          )
    if len(answers) == 0:
        embed.add_field(name="Oops!",
                        value="I'm sorry. I currently don't have the answers to a puzzle. Please try another "
                              f"{PREFIX}puzzle")
    elif len(follow_ups) > 0:
        embed.add_field(name="Answer", value=f"The best move is {answers.pop(0)}. "
                                             f"The opponent responded with {follow_ups.pop(0)}, now what's the best"
                                             f"move?")
    else:
        embed.add_field(name="Answer", value=f"The best move is {answers.pop(0)}. That's the end of the puzzle!")

    await message.channel.send(embed=embed)
