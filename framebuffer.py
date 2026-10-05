import numpy as np

class Framebuffer:
    def __init__(self, device="/dev/fb1", width=480, height=320):
        self.device = device
        self.width = width
        self.height = height

    def show(self, surface):
        rgb = np.asarray(
            __import__("pygame").surfarray.array3d(surface)
        )
        rgb = np.transpose(rgb, (1, 0, 2))

        r = rgb[:, :, 0].astype(np.uint16)
        g = rgb[:, :, 1].astype(np.uint16)
        b = rgb[:, :, 2].astype(np.uint16)

        rgb565 = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)

        with open(self.device, "wb") as fb:
            fb.write(rgb565.astype("<u2").tobytes())
