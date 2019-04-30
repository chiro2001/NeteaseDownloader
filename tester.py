from tkinter import *

class MenuDemo:
    def hello(self):
        print("hello!")

    def __init__(self):


        window = Tk()
        window.title("Menu demo")


        menubar = Menu(window)
        window.config(menu = menubar)

        #创建下拉菜单，并添加到菜单条
        operationMenu = Menu(menubar, tearoff = 0)
        menubar.add_cascade(label = "操作", menu = operationMenu)
        operationMenu.add_command(label = "加", command = self.add)
        operationMenu.add_command(label="减", command=self.subtract)
        operationMenu.add_separator()
        operationMenu.add_command(label = "乘", command = self.multiply)
        operationMenu.add_command(label="除", command=self.divide)

        exitMenu = Menu(menubar, tearoff = 0)
        menubar.add_cascade(label = "退出", menu = exitMenu)
        exitMenu.add_command(label = "退出", command = window.quit)

        mainloop()

    def add(self):
        print("相加")
    def subtract(self):
        print("相减")
    def multiply(self):
        print("相乘")
    def divide(self):
        print("相除")

MenuDemo()
