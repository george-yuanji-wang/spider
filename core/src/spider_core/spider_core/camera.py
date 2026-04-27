import cv2
import sys

def test_camera(index=0):
    printf(f'Trying /dev/video{index}')
    cap = cv2.VideoCapture(index)

    if not cap.isOpened():
        print(f'Failed to open /dev/video{index}')
        return False

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    print(f'Opened! Resolution: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}')
    print('Press q to quit')

    while True:
        ret, frame = cap.read()
        if not ret:
            print('Failed to grab frame')
            break
        cv2.imshow('camera test', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()

    return True

if __name__ == '__main__':
    if len(sys.argv) > 1:
        test_camera(int(sys.argv[1]))
    else:
        print('Scanning for cameras...')
        found = False
        for i in range(6):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                print(f'Found camera at index {i}')
                cap.release()
                found = True
        if not found:
            print('No cameras found')
        else:
            idx = int(input('Enter index to test:'))
            test_camera(idx)