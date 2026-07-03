# coding:UTF-8
import time
import struct
import bleak
import asyncio


# 设备实例 Device instance
class DeviceModel:
    # region 属性 attribute
    # 设备名称 deviceName
    deviceName = "我的设备"

    # 设备数据字典 Device Data Dictionary
    deviceData = {}

    # 设备是否开启
    isOpen = False

    # 临时数组 Temporary array
    TempBytes = []

    # endregion

    def __init__(self, deviceName, mac, callback_method):
        print("初始化设备模型")
        # 设备名称（自定义） Device Name
        self.deviceName = deviceName
        self.mac = mac
        self.client = None
        self.writer_characteristic = None
        self.isOpen = False
        self.callback_method = callback_method
        self.deviceData = {}

    # region 获取设备数据 Obtain device data
    # 设置设备数据 Set device data
    def set(self, key, value):
        # 将设备数据存到键值 Saving device data to key values
        self.deviceData[key] = value

    # 获得设备数据 Obtain device data
    def get(self, key):
        # 从键值中获取数据，没有则返回None Obtaining data from key values
        if key in self.deviceData:
            return self.deviceData[key]
        else:
            return None

    # 删除设备数据 Delete device data
    def remove(self, key):
        # 删除设备键值
        del self.deviceData[key]

    # endregion

    # 打开设备 open Device
    async def openDevice(self):
        print("Opening device......")
        # 获取设备的服务和特征 Obtain the services and characteristic of the device
        async with bleak.BleakClient(self.mac) as client:
            self.client = client
            self.isOpen = True
            # 设备UUID常量 Device UUID constant
            target_service_uuid = "0000ffe5-0000-1000-8000-00805f9a34fb"
            target_characteristic_uuid_read = "0000ffe4-0000-1000-8000-00805f9a34fb"
            target_characteristic_uuid_write = "0000ffe9-0000-1000-8000-00805f9a34fb"
            notify_characteristic = None

            print("Matching services......")
            for service in client.services:
                if service.uuid == target_service_uuid:
                    print(f"Service: {service}")
                    print("Matching characteristic......")
                    for characteristic in service.characteristics:
                        if characteristic.uuid == target_characteristic_uuid_read:
                            notify_characteristic = characteristic
                        if characteristic.uuid == target_characteristic_uuid_write:
                            self.writer_characteristic = characteristic
                    if notify_characteristic:
                        break

            if notify_characteristic:
                print(f"Characteristic: {notify_characteristic}")
                # 设置通知以接收数据 Set up notifications to receive data
                await client.start_notify(notify_characteristic.uuid, self.onDataReceived)

                # 保持连接打开 Keep connected and open
                # try:
                #     while self.isOpen:
                #         await asyncio.sleep(1)
                # except asyncio.CancelledError:
                #     pass
                # finally:
                #     # 在退出时停止通知 Stop notification on exit
                #     await client.stop_notify(notify_characteristic.uuid)
                # Keep connected and actively poll for Quaternions
                try:
                    while self.isOpen:
                        # Actively request the Quaternion register (0x51)
                        await self.readReg(0x51)
                        # Poll at 20Hz to avoid flooding the BLE adapter
                        await asyncio.sleep(0.05)
                except asyncio.CancelledError:
                    pass
                finally:
                    await client.stop_notify(notify_characteristic.uuid)
            else:
                print("No matching services or characteristic found")

    # 关闭设备  close Device
    def closeDevice(self):
        self.isOpen = False
        print("The device is turned off")

    # region 数据解析 data analysis
    # 串口数据处理  Serial port data processing
    # def onDataReceived(self, sender, data):
    #     tempdata = bytes.fromhex(data.hex())
    #     for var in tempdata:
    #         self.TempBytes.append(var)
    #         if len(self.TempBytes) == 2 and (self.TempBytes[0] != 0x55 or self.TempBytes[1] != 0x61):
    #             del self.TempBytes[0]
    #             continue
    #         if len(self.TempBytes) == 20:
    #             self.processData(self.TempBytes[2:])
    #             self.TempBytes.clear()

    # Replace the existing onDataReceived with this robust parser
    # def onDataReceived(self, sender, data):
    #     tempdata = bytes.fromhex(data.hex())
    #     for var in tempdata:
    #         self.TempBytes.append(var)
    #
    #         # Validate the 0x55 header
    #         if len(self.TempBytes) == 1 and self.TempBytes[0] != 0x55:
    #             self.TempBytes.clear()
    #             continue
    #
    #         # Allow both the 20-byte BLE packet (0x61) and 11-byte Quaternion packet (0x59)
    #         if len(self.TempBytes) == 2 and self.TempBytes[1] not in [0x61, 0x59]:
    #             self.TempBytes.pop(0)
    #             continue
    #
    #         # Parse the 20-byte Acc/Gyro/Euler packet
    #         if len(self.TempBytes) == 20 and self.TempBytes[1] == 0x61:
    #             self.processData(self.TempBytes[2:])
    #             self.TempBytes.clear()
    #
    #         # Parse the 11-byte Quaternion packet
    #         elif len(self.TempBytes) == 11 and self.TempBytes[1] == 0x59:
    #             self.processQuaternion(self.TempBytes[2:])
    #             self.TempBytes.clear()

    def onDataReceived(self, sender, data):
        tempdata = bytes.fromhex(data.hex())
        for var in tempdata:
            self.TempBytes.append(var)

            # Validate the 0x55 header
            if len(self.TempBytes) == 1 and self.TempBytes[0] != 0x55:
                self.TempBytes.clear()
                continue

            # Allow both standard 0x61 and register return 0x71 packets
            if len(self.TempBytes) == 2 and self.TempBytes[1] not in [0x61, 0x71]:
                self.TempBytes.pop(0)
                continue

            # Parse the 20-byte packet
            if len(self.TempBytes) == 20:
                if self.TempBytes[1] == 0x61:
                    # Ignore Euler angles to prevent Gimbal Lock
                    pass
                elif self.TempBytes[1] == 0x71:
                    # Validate the returned data is from the Quaternion register (0x51)
                    if self.TempBytes[2] == 0x51 and self.TempBytes[3] == 0x00:
                        self.processQuaternion(self.TempBytes[4:])
                self.TempBytes.clear()

    # 数据解析 data analysis
    def processData(self, Bytes):
        Ax = self.getSignInt16(Bytes[1] << 8 | Bytes[0]) / 32768 * 16
        Ay = self.getSignInt16(Bytes[3] << 8 | Bytes[2]) / 32768 * 16
        Az = self.getSignInt16(Bytes[5] << 8 | Bytes[4]) / 32768 * 16
        Gx = self.getSignInt16(Bytes[7] << 8 | Bytes[6]) / 32768 * 2000
        Gy = self.getSignInt16(Bytes[9] << 8 | Bytes[8]) / 32768 * 2000
        Gz = self.getSignInt16(Bytes[11] << 8 | Bytes[10]) / 32768 * 2000
        AngX = self.getSignInt16(Bytes[13] << 8 | Bytes[12]) / 32768 * 180
        AngY = self.getSignInt16(Bytes[15] << 8 | Bytes[14]) / 32768 * 180
        AngZ = self.getSignInt16(Bytes[17] << 8 | Bytes[16]) / 32768 * 180
        self.set("AccX", round(Ax, 3))
        self.set("AccY", round(Ay, 3))
        self.set("AccZ", round(Az, 3))
        self.set("AsX", round(Gx, 3))
        self.set("AsY", round(Gy, 3))
        self.set("AsZ", round(Gz, 3))
        self.set("AngX", round(AngX, 3))
        self.set("AngY", round(AngY, 3))
        self.set("AngZ", round(AngZ, 3))
        self.callback_method(self)

    def processQuaternion(self, Bytes):
        # Calculate Quaternions q0, q1, q2, q3
        q0 = self.getSignInt16(Bytes[1] << 8 | Bytes[0]) / 32768.0
        q1 = self.getSignInt16(Bytes[3] << 8 | Bytes[2]) / 32768.0
        q2 = self.getSignInt16(Bytes[5] << 8 | Bytes[4]) / 32768.0
        q3 = self.getSignInt16(Bytes[7] << 8 | Bytes[6]) / 32768.0

        self.set("q0", round(q0, 5))
        self.set("q1", round(q1, 5))
        self.set("q2", round(q2, 5))
        self.set("q3", round(q3, 5))

        # Trigger the callback to print the updated dictionary
        self.callback_method(self)

    # 获得int16有符号数 Obtain int16 signed number
    @staticmethod
    def getSignInt16(num):
        if num >= pow(2, 15):
            num -= pow(2, 16)
        return num

    # endregion

    # 发送串口数据 Sending serial port data
    # def sendData(self, data):
    #     try:
    #         if self.client is not None and self.writer_characteristic is not None:
    #             self.client.write_value(self.writer_characteristic.uuid, data)
    #     except Exception as ex:
    #         print(ex)

    # Change these functions to async
    async def sendData(self, data):
        try:
            if self.client is not None and self.writer_characteristic is not None:
                # Critical fix: The correct bleak method is write_gatt_char
                await self.client.write_gatt_char(self.writer_characteristic.uuid, bytearray(data))
        except Exception as ex:
            print(f"Write error: {ex}")

    async def readReg(self, regAddr):
        await self.sendData(self.get_readBytes(regAddr))

    # 读取寄存器 read register
    # def readReg(self, regAddr):
        # 封装读取指令并向串口发送数据 Encapsulate read instructions and send data to the serial port
        # self.sendData(self.get_readBytes(regAddr))

    # 写入寄存器 Write Register
    def writeReg(self, regAddr, sValue):
        # 解锁 unlock
        self.unlock()
        # 延迟100ms Delay 100ms
        time.sleep(0.1)
        # 封装写入指令并向串口发送数据
        self.sendData(self.get_writeBytes(regAddr, sValue))
        # 延迟100ms Delay 100ms
        time.sleep(0.1)
        # 保存 save
        self.save()

    # 读取指令封装 Read instruction encapsulation
    @staticmethod
    def get_readBytes(regAddr):
        # 初始化
        tempBytes = [None] * 5
        tempBytes[0] = 0xff
        tempBytes[1] = 0xaa
        tempBytes[2] = 0x27
        tempBytes[3] = regAddr
        tempBytes[4] = 0
        return tempBytes

    # 写入指令封装 Write instruction encapsulation
    @staticmethod
    def get_writeBytes(regAddr, rValue):
        # 初始化
        tempBytes = [None] * 5
        tempBytes[0] = 0xff
        tempBytes[1] = 0xaa
        tempBytes[2] = regAddr
        tempBytes[3] = rValue & 0xff
        tempBytes[4] = rValue >> 8
        return tempBytes

    # 解锁
    def unlock(self):
        cmd = self.get_writeBytes(0x69, 0xb588)
        self.sendData(cmd)

    # 保存
    def save(self):
        cmd = self.get_writeBytes(0x00, 0x0000)
        self.sendData(cmd)
