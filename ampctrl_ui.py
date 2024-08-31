import sys,os,configparser,json,traceback
import threading
from PyQt5 import QtWidgets,uic
from PyQt5.QtWidgets import *
from PyQt5.QtGui import QPixmap,QResizeEvent,QIcon
from PyQt5.QtCore import *
import bleak
import asyncio

dir=os.path.dirname(sys.argv[0])
os.chdir(dir)
sys.path.append(dir)

ui=os.path.join(dir,"main.ui")

CFGFILE="ampctrl.cfg"
CHAR_WRITE="0000ae10-0000-1000-8000-00805f9b34fb"
CHAR_NOTIFY="0000ae04-0000-1000-8000-00805f9b34fb"

cfgParser=configparser.ConfigParser()
cfgParser.read(CFGFILE)
if not cfgParser.has_section("Common"):
    cfgParser.add_section("Common")

def writeConfig():
    with open(CFGFILE,"w") as f:
        cfgParser.write(f)

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

class App(QtWidgets.QMainWindow):
    buttonLink:QToolButton
    buttonPrev:QToolButton
    buttonPlay:QToolButton
    buttonPause:QToolButton
    buttonNext:QToolButton
    buttonVolume:QToolButton
    verticalLayout:QVBoxLayout
    selectDevice:QComboBox
    selectMode:QComboBox
    sliderVolume:QSlider

    device:str
    scannedDevices:dict={}
    connected=False

    scanner:bleak.BleakScanner=None
    client:bleak.BleakClient=None
    stop_scan_event:asyncio.Event=None
    
    loop:asyncio.AbstractEventLoop=None

    def __init__(self):
        super(App, self).__init__()
        uic.loadUi(ui, self)
        self.loop=asyncio.new_event_loop()
        self.device=cfgParser.get("Common","lastDevice",fallback="")
        self.selectDevice.addItem(self.device)
        self.selectDevice.setCurrentText(self.device)
        self.centralWidget().setLayout(self.verticalLayout)
        self.buttonLink.clicked.connect(self.connectOrDisconnect)
        self.sliderVolume.sliderReleased.connect(self.setVolume)
        self.show()
        self.setControlsEnabled(False)
        self.startScan()
    def setControlsEnabled(self,enabled):
        self.buttonPrev.setEnabled(enabled)
        self.buttonNext.setEnabled(enabled)
        self.buttonPause.setEnabled(enabled)
        self.buttonPlay.setEnabled(enabled)
        self.buttonVolume.setEnabled(enabled)
        self.sliderVolume.setEnabled(enabled)
    def startScan(self):
        scanthread=threading.Thread(target=asyncio.run,args=(self.scan(),))
        scanthread.start()
    async def scan(self):
        # self.scanner=bleak.BleakScanner(detection_callback=self.onScanned)
        self.stop_scan_event = asyncio.Event()
        # await self.scanner.start()
        async with bleak.BleakScanner(detection_callback=self.onScanned,service_uuids=["00001812-0000-1000-8000-00805f9b34fb"]) as scanner:
            await self.stop_scan_event.wait()
    def resizeEvent(self, event:QResizeEvent):
        new_size = event.size()

    async def onScanned(self,device,data):
        # print(device,"|",data)
        if device.address not in self.scannedDevices:
            self.scannedDevices[device.address]=device
            self.selectDevice.addItem(device.__str__(),device.address)
    def connectOrDisconnect(self):
        if not self.connected:
            self.loop.run_until_complete(self.connect())
            # asyncio.run(self.connect())
        else:
            self.loop.run_until_complete(self.disconnect())
            # asyncio.run(self.disconnect())
    async def connect(self):
        addr=self.selectDevice.currentText().split(": ")[0]
        if addr.__len__()==0:
            return
        self.client=bleak.BleakClient(addr)
        await self.client.connect()
        self.device=self.selectDevice.currentText()
        cfgParser.set("Common","lastDevice",self.device)
        writeConfig()
        if self.client.is_connected:
            print("Connected to "+self.client.address)
            self.stop_scan_event.set()
            self.connected=True
            self.setControlsEnabled(True)
            self.buttonLink.icon=QIcon.fromTheme("network-disconnect")
        pass
    async def disconnect(self,scan=True):
        if not self.client:
            return
        await self.client.disconnect()
        print("Disconnected")
        self.setControlsEnabled(False)
        self.connected=False
        if scan:
            self.startScan()

    def setVolume(self):
        value=self.sliderVolume.value()
        self.loop.run_until_complete(setVolume(self.client,value))
        print("Set volume to "+str(value))
        # asyncio.run(setVolume(self.client,value))

app = QtWidgets.QApplication(sys.argv)
window=App()
# window = uic.loadUi(ui)
# if window==None:
#     exit()
try:
    window.show()
    app.exec()
finally:
    window.stop_scan_event.set()
    window.loop.run_until_complete(window.disconnect(False))
