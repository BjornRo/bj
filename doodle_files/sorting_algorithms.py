""" 
Usage:
import sorting_algorithms as SA

    To sort:
    SA.sort("your algorithm",array)

    Example:
    sortedlist = SA.sort("BubbleSort", [4,5,3,6,7,4,3,2])

Sorting algorithms:
    bubbleSort
    combSort
    insertionSort
    selectionSort
    mergeSort
    quickSort
    heapSort

"""

#For OOP:
#Could made into a class with two helper functions and then inherit them into subclasses.
#Or into an Template Method/Strategy pattern. Preferably Strategy pattern.

#I'm Lazy and this is "functional" programming.
#Just select your sorting function and your chosen array.

#Tuple swap. Temp swap is also an option.
def _swap(array, i, j):
    array[i], array[j] = array[j], array[i]

#Check if array is an array. If it is an array, return its length.
def _checkArrayGetLength(array):
    if isinstance(array,list):
        return len(array)
    else:
        raise ValueError("Invalid list/array entered")

"""
Store length of the array into variable. 
Otherwise it's called as many times as algorithms worst case time complexity.

This solution:
O(1) Memory usage + O(1) executions
"""



""" 
BubbleSort implemented with Flag-indicator to indicate if a swap
has been made. If no swaps occured, then the list is sorted.
Stable sorting, in-place.

Still same time complexity. 
T(n) = 
Best case: O(n)
Worst case: O(n^2)
Average: O(n^2)
"""
def bubbleSort(array):
    if (arrayLen := _checkArrayGetLength(array)) <= 1:
        return array
    else:
        #We're checking n+1 in list, thus move length one less to prevent OutOfBounds.
        arrayLen -= 1

        #Flag to check if any swaps has been made. No swaps -> Ordered list.
        flag = True
        while flag:
            flag = False

            #If a swap occured, then set flag as 'True' and swap element.
            for i in range(arrayLen):
                if array[i] > array[i+1]:
                    _swap(array, i, i+1)
                    flag = True
    return array

""" 
Comb sort
Faster than Bubblesort on average.
Unstable, in-place.

T(n) = 
Best case: O(n log n)
Worst case: O(n^2)
Average: O(n^2)
"""
def combSort(array):
    if (arrayLen := _checkArrayGetLength(array)) <= 1:
        return array
    else:
        gap = arrayLen
        shrink = 1.3
        flag = True
        while flag:
            #Shrink gap/comb for each loop.
            gap = int(gap/shrink)

            #If statement: Last check, if there are no swaps, we're done.
            if gap <= 1:
                gap = 1
                flag = False

            #Move "comb" with i and swap if necessary.
            for i in range(arrayLen-gap):
                if array[i] > array[i+gap]:
                    _swap(array,i,i+gap)
                    flag = True
    return array

"""
Insertion sort

Stable, in-place.
T(n) = 
Best case: O(n)
Worst case: O(n^2)
Average: O(n^2)
"""
def insertionSort(array):
    if (arrayLen := _checkArrayGetLength(array)) <= 1:
        return array
    else:
        #Iterate through all elements.
        for i in range(arrayLen-1):
            #Store element to be compared
            temp = array[i+1]
            n = i
            #While loop to move each element down until 2nd statement becomes false. 
            #Then overwrite the n-th spot. Since while loop left n-1 we have to add n+1 in the else statement.
            while (n >= 0) and (array[n] > temp):
                array[n+1] = array[n]
                n -= 1
            else:
                array[n+1] = temp 
    return array

"""
Selection sort

Stable, in-place.
T(n) = 
Best case: O(n^2)
Worst case: O(n^2)
Average: O(n^2)
"""
def selectionSort(array):
    if (arrayLen := _checkArrayGetLength(array)) <= 1:
        return array
    else:
        #Iterate through all elements
        for i in range(arrayLen-1):
            #Set first element as min.
            minValueIndex = i

            #Find the smallest element between i+1 to n. Do this for all i to n.
            for j in range(i,arrayLen):
                if array[j] < array[minValueIndex]:
                    minValueIndex = j
            #If a smaller element is found. Swap i and j (index of the smallest element). 
            #Else do nothing.
            if (minValueIndex != i):
                _swap(array,i,minValueIndex)
    return array

"""
Merge Sort

Stable, out-of-place.
T(n) = 
Best case: O(n log n)
Worst case: O(n log n)
Average: O(n log n)

Could be broken into "smaller" functions but this hides the helper function from the global scope.
Also refactorized into overloading. 

Function starts from mergeSort return.
"""
def mergeSort(array):
    if (arrayLen := _checkArrayGetLength(array)) <= 1:
        return array
    else:
        #Function to split the arrays into smaller arrays.
        def mergeSortSplit(array, start, end):
            #Statement to proceed or stop the recursive calls.
            if start < end:
                #Split the arrays into two. Divide and conquer.
                split = int((start+end)/2)
                #Call this function until there's only 1 element left due to (start < end) statement.
                return mergeSortMerge(mergeSortSplit(array, start, split),mergeSortSplit(array, split+1, end))
            else:
                #Base case, return the lonely element and collapse the stack back to be sorted.
                return array[start:start+1]
        
        #The actual merge phase. This function combine and sort the arrays.
        def mergeSortMerge(left, right):
            totalLength = len(left) + len(right)
            newArray = []
            leftIndex, rightIndex = 0, 0
            while len(newArray) < totalLength:
                #First check if both left and right contains any elements.
                if (leftIndex < len(left)) and (rightIndex < len(right)):
                    #Check which array has the smallest item at their
                    #respective current index.
                    if left[leftIndex] < right[rightIndex]:
                        newArray.append(left[leftIndex])
                        leftIndex += 1
                    else:
                        newArray.append(right[rightIndex])
                        rightIndex += 1
                #If left or right is empty, then we just add the rest since
                #we know that the rest of the array is sorted.
                else:
                    #Helper function to add the rest of the elements as a last step.
                    def fillRest(array, index):
                        while index < len(array):
                            newArray.append(array[index])
                            index += 1
                    #Check which array is empty and add rest of the not empty array into the new array.
                    if leftIndex >= len(left):
                        fillRest(right, rightIndex)
                    else:
                        fillRest(left, leftIndex)
            return newArray
    return mergeSortSplit(array, 0, arrayLen-1)

"""
Quick sort
Unstable, out-of-place

T(n) = 
Best case: O(n log n)
Worst case: O(n^2)
Average: O(n log n)

Super messy code since everything is contained into 1 function.
"""
def quickSort(array, start = None, stop = None):
    if (arrayLen := _checkArrayGetLength(array)) <= 1:
        return array
    else:
        #Partition function. pivotChooser: <-1: first, 0/None: median of 3, >1: high
        def partition(array,start,stop,pivotChooser = None):
            pivot = None
            if pivotChooser < 0:
                pivot = array[start]
            elif pivotChooser > 0:
                pivot = array[stop]
            else:
                pivot = array[int((start+stop)/2)]
            
            #Partition algorithm
            left, right = start, stop
            while True:
                #Find where pivot should be swapped to.
                #If left-cursor-index element is larger than pivot, move left-cursor right until
                #it finds an element larger/equal than pivot.
                while array[left] < pivot:
                    left += 1

                #If right-cursor-index element is larger than pivot, move right-cursor left until
                #it finds an element smaller/equal than pivot.
                while array[right] > pivot:
                    right -= 1

                #Break loop if left-/right-cursors is equal or passed each other.
                if left >= right:
                    return right

                #Swap
                _swap(array,left,right)
                #Advance cursors one step 'inwards' and continue until left and right passed each other.
                left += 1
                right -= 1

        #First statement to start the sorting algorithm
        if start == None and stop == None:
            quickSort(array,0,arrayLen-1)

        #If start index is bigger than stop index. Algorithm finished.
        elif start < stop:
            #Partition border to split function into two parts
            partition_border = partition(array,start,stop,-1)

            #Lower border sorting
            quickSort(array,start,partition_border)
            #Upper border sorting
            quickSort(array,partition_border+1,stop)
        return array


""" 
Heap sort

Unstable, in-place.
T(n) = 
Best case: O(n log n)
Worst case: O(n log n)
Average: O(n log n)
"""

def heapSort(array):
    if (arrayLen := _checkArrayGetLength(array)) <= 1:
        return array
    else:
        def heapify(array, n, i):
            #Set parent as largest, and define index of its children
            largest = i
            left, right = i*2+1, i*2+2

            #Check if parent has child nodes. If children exists, then check which is smaller or bigger.(Depends on max-/minheap)
            #If a child is bigger than the parent,
            #select its index and swap it and the parent.
            if left < n and array[i] < array[left]:
                largest = left
            if right < n and array[largest] < array[right]:
                largest = right

            #If parent node is larger than its children, 
            #do nothing and continue on comparing rest of the tree with its children.
            if largest != i:
                _swap(array,i,largest)
                #If a swap occurs, recursivly call the function with the largest index.
                #Because we swapped the parent and the child, and now the 'old parent' has to be compared to its new children.
                #If we don't recursivly check/swap, the 'old parent' may end up smaller than its new children, 
                #which breaks heap invariant.
                heapify(array,n,largest)

        for i in range(arrayLen//2-1,-1,-1):
            heapify(array,arrayLen,i)

        for i in range(arrayLen-1, 0, -1): 
            _swap(array,i,0)
            heapify(array,i,0) 
    return array

"""
Driver code:
"""
#exec(open("sorting_algorithms.py").read(), globals())
#python -i sorting_algorithms.py

#Reload file.
#def r():
#    exec(open("sorting_algorithms.py").read(), globals())

def _getSortFunc(string):
    sortAlgo = {
        "bubb": bubbleSort,
        "comb": combSort,
        "inse": insertionSort,
        "sele": selectionSort,
        "merg": mergeSort,
        "quic": quickSort,
        "heap": heapSort,
    }
    if isinstance(string,str): 
        #Only keep first 4 letters from key(string). User can write: "quicksort" and it will work.
        key = string.lower()[0:4] 
        value = sortAlgo.get(key)
        if value == None:
            raise ValueError("Invalid sorting algorithm chosen")
        else:
            return value
    else:
        raise ValueError("Enter a valid string!")

def sort(sortingAlgorithmString,array):
    return _getSortFunc(sortingAlgorithmString)(array)

#expectedList = [3,4,4,5,5,6,6,7,9]
#randomList = [9,4,5,3,6,4,5,6,7]

#sortAlgorithm = "quick"
#sortedList = sort(sortAlgorithm,randomList)

#print("Selected sorting: " + sortAlgorithm)
#print(sortedList == expectedList)