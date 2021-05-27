import pickle
import matplotlib.pyplot as plt
colors = [(0,0,0),(255,0,0),(0,0,255),(100,100,100),(127,0,255)]
with open('Data_save.pkl','rb') as f:
    data = pickle.load(f)
for i, key in enumerate(data.keys()):
    clr = colors[i]
    plt.plot(data[key], color=(clr[0]/255,clr[1]/255,clr[2]/255))
plt.xlabel('Tid (Frames/Tidsenheter)', fontsize = 11)
plt.ylabel('Population (Antal)', fontsize = 11)
plt.legend(data.keys())
plt.show()
