# messagebox:消息弹框
# 不断点击按钮，切换各种弹窗
import tkinter as tk
from tkinter import messagebox
# from tk_center_win import set_win_center

root = tk.Tk()
root.title('消息框')
root.geometry('190x80+300+300')  # 设置窗口大小和位置
# set_win_center(root, 190, 80)  # 设置窗口大小并居中显示
n = 0
str_var = tk.StringVar()
str_var.set('askokcancel')


def cmd():
    '''弹框提示'''
    global n
    global str_var
    n += 1
    if n == 1:
        r = messagebox.askokcancel('消息框', 'askokcancel')
        print('askokcancel:', r)
        str_var.set('askquestion')
    elif n == 2:
        r = messagebox.askquestion('消息框', 'askquestion')
        print('askquestion:', r)
        str_var.set('askyesno')
    elif n == 3:
        r = messagebox.askyesno('消息框', 'askyesno')
        print('askyesno:', r)
        str_var.set('askretrycancel')
    elif n == 4:
        r = messagebox.askretrycancel('消息框', 'askretrycancel')
        print('askretrycancel:', r)
        str_var.set('showerror')
    elif n == 5:
        r = messagebox.showerror('消息框', 'showerror')
        print('showerror:', r)
        str_var.set('showinfo')
    elif n == 6:
        r = messagebox.showinfo('消息框', 'showinfo')
        print('showinfo:', r)
        str_var.set('showwarning')
    else:
        r = messagebox.showwarning('消息框', 'showwarning')
        print('showwarning:', r)
        str_var.set('askokcancel')
        n = 0


label = tk.Label(root, text='不断点击按钮，切换各种弹窗', font='微软雅黑 -14', pady=8)
label.grid()
btn = tk.Button(root, width='15', textvariable=str_var, command=cmd)
btn.grid()

root.mainloop()