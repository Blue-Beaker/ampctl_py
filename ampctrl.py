import asyncio
import os,sys,bleak,argparse

address="3A:A3:A2:30:E8:8D"

CHAR_WRITE="0000ae10-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY="0000ae04-0000-1000-8000-00805f9b34fb"

async def setVolume(client:bleak.BleakClient,volume:int):
    if ((volume < 32) and (volume >= 0)):
        data = [0x7e, 0x0f, 0x1d, 0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0xba]
        sum = 0

        data[3] = volume

        for i in range(data.__len__()):
            sum += data[i]

        data[data.__len__()-1] = (sum+0x46)%256
        bytedata=bytearray(data)
        # print(bytedata.hex())
        await client.write_gatt_char(CHAR_WRITE,bytedata,response=True)

def connectDevice(address:str):
    # os.system("bluetoothctl connect "+address)
    return bleak.BleakClient(address)

def writeValue(attribute:str,value:bytearray):
    os.system("bluetoothctl gatt.select-attribute "+attribute)
    os.system("bluetoothctl gatt.write "+value.hex())

def callback(sender, data: bytearray):
    print(f"{sender}: {data}")

# writeValue("0000ae10-0000-1000-8000-00805f9b34fb",bytearray())
async def main():
    async with bleak.BleakClient(address) as client:
        if not client.is_connected:
            await client.connect()
        await client.start_notify(CHAR_NOTIFY,callback)
        result=await client.read_gatt_char(CHAR_NOTIFY)
        print(result)
        while 1:
            await setVolume(client,int(input("Set Volume(0~31):")))

asyncio.run(main())