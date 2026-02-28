import psutil

def memory_percent_get():
    mem = psutil.virtual_memory()
    print(mem)
    percent = int(mem.percent)
    print(percent)
    return percent