data1 = [
    [0,1,0],
    [1,1,1],
    [0,1,0]
]

data2 = [
    [1,0,1],
    [0,1,0],
    [1,0,1]
]

data3 = [
    [1,1,1],
    [0,0,0],
    [1,1,1]
]

def mac(data0, data1):
    m = len(data0)
    acc = 0
    for i in range(m):
        for j in range(m):
            acc += data0[i][j] * data1[i][j]
    return acc

def pad(data, pad_size):
    m = len(data)
    p = pad_size
    re_data = [[0]*(m+p*2)]*(m+p*2)
    for i in range(m):
        for j in range(m):
            re_data[p+i][p+j] = data[i][j]
    return re_data

print(pad(data1, 3))

print(mac(data3,data2))