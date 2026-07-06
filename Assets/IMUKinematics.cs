using System;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

// This class perfectly matches your Python JSON payload
[Serializable]
public class IMUData
{
    public string id;
    public float q0; // w
    public float q1; // x
    public float q2; // y
    public float q3; // z
}

public class IMUKinematics : MonoBehaviour
{
    [Header("Network Settings")]
    public int udpPort = 5005;

    [Header("Robot Joints (Must match sensor order)")]
    [Tooltip("Drag the UR5 links here in order: e.g., shoulder_link, upper_arm_link, etc.")]
    public Transform[] robotJoints;

    // Internal Math Data
    private Quaternion[] rawGlobalQuats;
    private Quaternion[] offsetQuats;

    // Networking
    private Thread receiveThread;
    private UdpClient client;
    private bool isRunning = true;

    void Start()
    {
        int numSensors = 5; // Adjust if you add/remove sensors
        rawGlobalQuats = new Quaternion[numSensors];
        offsetQuats = new Quaternion[numSensors];

        for (int i = 0; i < numSensors; i++)
        {
            rawGlobalQuats[i] = Quaternion.identity;
            offsetQuats[i] = Quaternion.identity;
        }

        // Start UDP listener on a background thread so Unity doesn't freeze
        receiveThread = new Thread(new ThreadStart(ReceiveData));
        receiveThread.IsBackground = true;
        receiveThread.Start();
        Debug.Log("Unity UDP Listener started on port " + udpPort);
    }

    void ReceiveData()
    {
        client = new UdpClient(udpPort);
        IPEndPoint anyIP = new IPEndPoint(IPAddress.Any, 0);

        while (isRunning)
        {
            try
            {
                byte[] data = client.Receive(ref anyIP);
                string text = Encoding.UTF8.GetString(data);
                IMUData imu = JsonUtility.FromJson<IMUData>(text);

                // Parse the ID to array index (e.g., "Joint_1" -> 0)
                if (imu.id.StartsWith("Joint_"))
                {
                    int index = int.Parse(imu.id.Split('_')[1]) - 1;
                    if (index >= 0 && index < rawGlobalQuats.Length)
                    {
                        // WitMotion order is w(q0), x(q1), y(q2), z(q3)
                        // Unity expects x, y, z, w
                        rawGlobalQuats[index] = new Quaternion(imu.q1, imu.q2, imu.q3, imu.q0);
                    }
                }
            }
            catch (Exception) { /* Ignore thread abort exceptions on quit */ }
        }
    }

    void Update()
    {
        // Hit Spacebar to trigger T-Pose Calibration
        if (Input.GetKeyDown(KeyCode.Space))
        {
            Calibrate();
        }

        // Apply Math: Calculate local rotations from global sensor data
        for (int i = 0; i < robotJoints.Length; i++)
        {
            if (i >= rawGlobalQuats.Length || robotJoints[i] == null) continue;

            // Step A: Apply calibration offset
            Quaternion qCalibratedCurrent = offsetQuats[i] * rawGlobalQuats[i];

            // Step B: Forward Kinematics Extraction
            if (i == 0)
            {
                robotJoints[i].localRotation = qCalibratedCurrent;
            }
            else
            {
                Quaternion qCalibratedParent = offsetQuats[i - 1] * rawGlobalQuats[i - 1];
                Quaternion qParentInverse = Quaternion.Inverse(qCalibratedParent);
                Quaternion qLocal = qParentInverse * qCalibratedCurrent;

                robotJoints[i].localRotation = qLocal;
            }
        }
    }

    public void Calibrate()
    {
        for (int i = 0; i < rawGlobalQuats.Length; i++)
        {
            offsetQuats[i] = Quaternion.Inverse(rawGlobalQuats[i]);
        }
        Debug.Log("Sensors Calibrated to T-Pose.");
    }

    void OnApplicationQuit()
    {
        // Safely close the network port when you hit stop in Unity
        isRunning = false;
        if (client != null) client.Close();
        if (receiveThread != null) receiveThread.Abort();
    }
}