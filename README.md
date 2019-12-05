# Kinect-Skeleton-Tracker
Module for using Kinect for general purpose skeleton tracking

## Dependencies
[Libfreenect](https://github.com/OpenKinect/libfreenect),
[Openni2](https://github.com/occipital/openni2),
[NiTE2](https://github.com/dpengineering/NiTE2/archive/v1.0.0.tar.gz)

### Installing Dependencies
 `sudo apt install freenect libopenni2-0 libopenni2-dev opencv-python`

 NiTE2 must be kept in the same directory as tracker! Get the NiTE2 folder from the link above.

 If it does not work in the same directory (aka if the program complains that the libraries aren't in the right folder), move NiTE2 around based off where the error message says.


 Current code returns the angle between hands, change as needed.

 Example use:
 ```
 from .tracker import Tracker
 t = Tracker()
 for angle in t.stream():
         if angle is not None:
             print("Got angle: %1.2f", angle)
         else:
             print("Ramp down")
 ```
