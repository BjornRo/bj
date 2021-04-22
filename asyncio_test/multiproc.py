import multiprocessing


def worker(key, container):
    container['a'][key] = key
    container[key + "k"] = [[203,3,3, key],2,3]
    container[key] = 3


if __name__ == "__main__":
    multiprocessing.freeze_support()

    manager = multiprocessing.Manager()
    container = manager.dict()
    container['a'] = manager.dict()

    p1 = multiprocessing.Process(target=worker, args=('x', container))
    p2 = multiprocessing.Process(target=worker, args=('y', container))

    p1.start()
    p2.start()
    p1.join()
    p2.join()
    print(container.copy())
    print(container['a'].copy())
    print(container)