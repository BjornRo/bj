#Python 3

import random
# import time
import tkinter as tk
# from tkinter import *


class Person():
    def __init__(self, group, state):
        def getColor():
            if group == 0:
                return "blue"
            elif group == 1:
                return "red"
            else:
                return "white"
        self.group = group
        self.state = state
        self.color = getColor()


# Settings
grid = 100
# Distribution, None 50%. 0.5
ndist = 0.5
totaldist = [ndist, (1 - ndist) / 2]
# State treshhold
thrshld = 0.7

# Counter
total = 0
satisfied = 0
percentage = 0
iterations = 0

# Tkinter
width, height = 800, 800
rect_width, rect_height = width / grid, height / grid
root = tk.Tk()
root.title("Schellings model")
root.resizable(False, False)
frame = tk.Frame()
frame.pack()
canvas = tk.Canvas(frame, width=width, height=height+20)

# World matrix
matrix = None


def genWorld():
    global total
    global matrix
    matrix = [[None for i in range(grid)] for j in range(grid)]
    for i in range(grid):
        for j in range(grid):
            rNum = random.random()
            if rNum > totaldist[0]:
                matrix[i][j] = None
            elif rNum > totaldist[1]:
                matrix[i][j] = Person(0, None)
                total += 1
            else:
                matrix[i][j] = Person(1, None)
                total += 1


def getColor(person):
    if person == None:
        return "white"
    else:
        return person.color


def getText():
    return str("Percentage: %.2f%% || Iterations: %d" % (percentage, iterations))


# Function to get info about the grid and move persons.

# addColors, Helper function to canvas to add object to GUI


def addColors(y, x, person):
    x0, y0 = x * rect_width+2, y * rect_height+2
    x1, y1 = x0 + rect_width-1, y0 + rect_height-1
    canvas.create_oval(
        x0, y0, x1, y1, fill=getColor(person), width=0)


def updateMatrix():
    global matrix, satisfied
    canvas.delete("all")
    noneIndex = []
    toMove = []
    satisfied = 0
    for i, arr in enumerate(matrix):
        for j, person in enumerate(arr):
            addColors(i, j, person)
            if person != None:
                state = checkState(i, j)
                matrix[i][j].state = state
                if not state:
                    toMove.append(tuple([i, j]))
            else:
                noneIndex.append(tuple([i, j]))
    random.shuffle(noneIndex)
    canvas.pack()
    canvas.create_text(100, height+10, text=getText())
    movePerson(noneIndex, toMove)


def movePerson(noneIdx, mIdx):
    global matrix
    for idx in mIdx:
        if noneIdx == []:
            break
        nIdx = noneIdx.pop()
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
    # print("Percentage: %.2f%% || Iterations: %d" % (percentage, iterations))

#Colors only to update the canvas one last time when it's finished.

def colors():
    canvas.delete("all")
    for y, row in enumerate(matrix):
        for x, person in enumerate(row):
            x0, y0 = x * rect_width+2, y * rect_height+2
            x1, y1 = x0 + rect_width-1, y0 + rect_height-1
            canvas.create_rectangle(
                x0, y0, x1, y1, fill=getColor(person), width=0)
    canvas.create_text(100, height+10, text=getText())
    canvas.pack()

# Actual program


""" 
Very slow thought...
Less loops and comparisons would help alot.

tkinter isn't suited for such large amount of objects... or inefficient code...
"""


def main():
    if percentage < 100:
        updateMatrix()
        calcTotals()
        root.after(250, main)
    else:
        colors()


if __name__ == '__main__':
    genWorld()
    main()
    root.mainloop()


""" if __name__ == '__main__':
    genWorld()
    while (percentage < 100):
        updateMatrix()
        calcTotals()
        
        # time.sleep(1/100)
    else:
        print("Finished! Total segregation!") """
