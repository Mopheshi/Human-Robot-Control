import asyncio
import bleak
import device_model

import socket
import json

# 扫描到的设备 Scanned devices
devices = []

# Setup UDP Socket
UDP_IP = "127.0.0.1"
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


def updateData(DeviceModel):
    print(f"{DeviceModel.deviceName} [{DeviceModel.mac}]: {DeviceModel.deviceData}")


# 扫描蓝牙设备并过滤名称 Scan Bluetooth devices and filter names
async def scan():
    global devices
    print("Searching for Bluetooth devices......")
    try:
        devices = await bleak.BleakScanner.discover()
        print("Search ended")
        for d in devices:
            if d.name is not None and "WT" in d.name:
                print(d)
    except Exception as ex:
        print("Bluetooth search failed to start")
        print(ex)


def updateData(DeviceModel):
    # Create a payload identifying the sensor and its data
    payload = {
        "id": DeviceModel.deviceName,
        "q0": DeviceModel.deviceData.get("q0", 1.0),
        "q1": DeviceModel.deviceData.get("q1", 0.0),
        "q2": DeviceModel.deviceData.get("q2", 0.0),
        "q3": DeviceModel.deviceData.get("q3", 0.0)
    }

    # Print to console for debugging
    print(f"{payload['id']}: {payload}")

    # Broadcast via UDP
    sock.sendto(json.dumps(payload).encode('utf-8'), (UDP_IP, UDP_PORT))


# 数据更新时会调用此方法 This method will be called when data is updated
# def updateData(DeviceModel):
# 直接打印出设备数据字典 Directly print out the device data dictionary
# print(DeviceModel.deviceData)
# 获得X轴加速度 Obtain X-axis acceleration
# print(DeviceModel.get("AccX"))


# if __name__ == '__main__':
#     # 搜索设备 Search Device
#     asyncio.run(scan())
#     # 选择要连接的设备 Select the device to connect to
#     device_mac = None
#     user_input = input("Please enter the Mac address you want to connect to (e.g. DF:E9:1F:2C:BD:59)：")
#     for device in devices:
#         if device.address == user_input:
#             device_mac = device.address
#             break
#     if device_mac is not None:
#         # 创建设备 Create device
#         device = device_model.DeviceModel("MyBle5.0", device_mac, updateData)
#         asyncio.run(device.openDevice())
#     else:
#         print("No Bluetooth device corresponding to Mac address found!!")


if __name__ == '__main__':
    # Optional: Run scan if you forget your MAC addresses
    asyncio.run(scan())

    # Terminal Input for deterministic mapping
    print("\n--- SENSOR INITIALISATION ---")
    print("Ensure order matches physical bone hierarchy (e.g., LeftForearm, LeftBicep)")
    user_input = input("Enter sensor MAC addresses separated by commas:\n> ")

    if not user_input.strip():
        print("Error: No MAC addresses provided. Exiting.")
        exit()

    # Clean the input list
    mac_addresses = [mac.strip().upper() for mac in user_input.split(',')]

    # Dynamically instantiate device models
    devices = []
    for i, mac in enumerate(mac_addresses):
        # Naming them logically based on input order
        device_name = f"Joint_{i + 1}"
        devices.append(device_model.DeviceModel(device_name, mac, updateData))


    # Asynchronous execution block
    async def connect_all_sensors():
        print(f"\nAttempting concurrent connection to {len(devices)} sensors...")
        tasks = [device.openDevice() for device in devices]
        await asyncio.gather(*tasks)


    # Run with safe shutdown
    try:
        asyncio.run(connect_all_sensors())
    except KeyboardInterrupt:
        print("\nShutdown signal received. Closing Bluetooth sockets...")
        for device in devices:
            device.closeDevice()
