bubblesort :: Ord a => [a] -> [a]
bubblesort xs = bubble xs [] False

bubble (x:y:xs) ys _
    | x > y           = bubble (x:xs) (ys++[y]) True -- If swap, then set to True
bubble (x:xs) ys bool = bubble xs (ys++[x]) bool
bubble [] ys True     = bubble ys [] False           -- If any element is swapped, then call function again
bubble _  ys _        = ys                           -- If no element is swapped, list is sorted.