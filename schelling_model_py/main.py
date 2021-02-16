# Python 3

import random
import time
import pygame
import sys
import array as arr
import numpy as np


class Person():
    def __init__(self, group, state):
        def getColor():
            if group == 0:
                return blue
            elif group == 1:
                return red
            else:
                return white
        self.group = group
        self.state = state
        self.color = getColor()


# Settings
grid = 200
# Distribution, None 50%. 0.5
ndist = 0.5
totaldist = [ndist, (1 - ndist) / 2]
# State treshold
thrshld = 0.7
width, height = 800, 800
rect_width, rect_height = width / grid, height / grid


# Counter
total = 0
satisfied = 0
percentage = 0
iterations = 0

# Pygame
pygame.display.set_caption('Schelling model')
window = pygame.display.set_mode((width, height))
tickrate = pygame.time.Clock()

# Colors (R, G, B)
white = (255, 255, 255) #pygame.Color(255, 255, 255)
red = (255, 0, 0) #pygame.Color(255, 0, 0)
blue = (0, 0, 255) #pygame.Color(0, 0, 255)

# World matrix, Index with None. noneIdx to make program run more efficiently.
matrix = None
noneIdx = None
colorMat = np.ndarray((grid, grid, 3))

# Generates matrix populated with individuals and index for None.


def genWorld():
    global total, matrix, noneIdx
    # matrix = [[None for i in range(grid)] for j in range(grid)]
    totalNone = 0
    matrix = np.empty((grid, grid), dtype=object)
    for i in range(grid):
        for j in range(grid):
            rNum = random.random()
            if rNum > totaldist[0]:
                matrix[i][j] = None
                setColor(i, j, None)
                totalNone += 1
            elif rNum > totaldist[1]:
                matrix[i][j] = Person(0, None)
                setColor(i, j, matrix[i][j])
                total += 1
            else:
                matrix[i][j] = Person(1, None)
                setColor(i, j, matrix[i][j])
                total += 1
    noneIdx = np.empty(totalNone, dtype=tuple)


def setColor(i, j, person):
    global colorMat
    colorMat[i][j] = getColor(person)


def getColor(person):
    if person == None:
        return white
    else:
        return person.color


def getStats():
    return str("Percentage: %.2f%% || Iterations: %d" % (percentage, iterations))


# Function to get info about the grid and move persons.
# addColors, Helper function to canvas to add object to GUI
def addColors(y, x, person):
    x0, y0 = x * rect_width+1, y * rect_height+1
    x1, y1 = x0 + rect_width-1, y0 + rect_height-1
    pygame.draw.rect(window, getColor(person), pygame.Rect(x0, y0, x1, x1))


def updateMatrix():
    global matrix, satisfied, noneIdx
    toMove = np.empty(int(grid*grid*(1-ndist)), dtype=tuple)
    moveCount, noneCount, satisfied = 0, 0, 0
    for i, arr in enumerate(matrix):
        for j, person in enumerate(arr):
            setColor(i, j, person)
            #addColors(i, j, person)
            if person != None:
                state = checkState(i, j)
                matrix[i][j].state = state
                if not state:
                    toMove[moveCount] = tuple([i, j])
                    moveCount += 1
            else:
                noneIdx[noneCount] = tuple([i, j])
                noneCount += 1
    random.shuffle(noneIdx)
    movePerson(toMove)


def movePerson(toMove):
    global matrix, noneIdx
    for i, idx in enumerate(toMove):
        if i > len(noneIdx) or idx == None:
            break
        nIdx = noneIdx[i]
        matrix[nIdx[0]][nIdx[1]] = matrix[idx[0]][idx[1]]
        matrix[idx[0]][idx[1]] = None


# Function to see person state. True if it should stay. False move.


def checkState(i, j):
    global satisfied
    isEqual = -1
    notEqual = 0
    for row in range(-1, 2):
        for col in range(-1, 2):
            if 0 <= row+i and row+i < grid and 0 <= col+j and col+j < grid:
                if matrix[row+i][col+j] != None:
                    if matrix[i][j].group == matrix[row+i][col+j].group:
                        isEqual += 1
                    else:
                        notEqual += 1

    total = isEqual + notEqual
    try:
        ratio = isEqual / total
    except ZeroDivisionError:
        ratio = 0

    if ratio > thrshld or total == 0:
        satisfied += 1
        return True
    else:
        return False


def calcTotals():
    global iterations, percentage
    iterations += 1
    percentage = (satisfied / total) * 100
    print("Percentage: %.2f%% || Iterations: %d" % (percentage, iterations))

# Colors only to update the canvas one last time when it's finished.

# Actual program


""" 
Very slow thought...

TODO
https://www.reddit.com/r/pygame/comments/9gyjaq/rendering_a_small_numpy_array_in_pygame/

Instead of adding each object, why not just add the array? Hmm...
"""


def draw():
    for y, row in enumerate(matrix):
        for x, person in enumerate(row):
            x0, y0 = x * rect_width+1, y * rect_height+1
            x1, y1 = x0 + rect_width-1, y0 + rect_height-1
            pygame.draw.rect(window, getColor(person),
                             pygame.Rect(x0, y0, x1, x1))

surf = None
def surf():
    global surf
    surf = pygame.Surface((grid, grid))
    pygame.surfarray.blit_array(surf, colorMat)
    surf = pygame.transform.scale(surf, (width, height))

def main():
    genWorld()
    surf()
    finish = True
    while (True):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

        # draw()
        pygame.display.update()
        if (percentage >= 100):
            tickrate.tick(10)
            if finish:
                finish = False
                print("Finished! Total segregation!")
                #draw()
        else:
            window.fill(white)
            updateMatrix()
            getStats()
            calcTotals()

            window.fill((0, 0, 0))           
            # blit the transformed surface onto the screen
            window.blit(surf, (0, 0))
            pygame.display.update()
            tickrate.tick(100)
    else:
        print("Finished! Total segregation!")


if __name__ == '__main__':
    main()
