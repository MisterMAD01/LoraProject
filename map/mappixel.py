import matplotlib.pyplot as plt
import matplotlib.image as mpimg

# โหลดภาพ
img = mpimg.imread('map.jpg')  # เปลี่ยนชื่อไฟล์ภาพตามของคุณ

# ฟังก์ชันเมื่อคลิกเมาส์
def on_click(event):
    if event.inaxes:  # ตรวจว่าอยู่ในกรอบภาพหรือไม่
        x = int(event.xdata)
        y = int(event.ydata)
        print(f'click: X={x}, Y={y}')

# แสดงภาพพร้อมกริด
fig, ax = plt.subplots()
ax.imshow(img)
ax.set_title("pixel X,Y")
ax.grid(True, color='white')  # เปิดกริดสีขาว (ปรับได้)

# เชื่อม event
cid = fig.canvas.mpl_connect('button_press_event', on_click)

plt.show()