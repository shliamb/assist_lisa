import psutil

def memory_percent_get():
    mem = psutil.virtual_memory()
    percent = int(mem.percent)
    return percent