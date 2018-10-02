from scipy import optimize
import numpy as np
''' A module that porvides multiple fitting methods '''


def fit_circle(points):
    '''Least-Square of the data-points to a circle'''

    try:
        x = points['x']
        y = points['y']
    except (KeyError, ValueError):
        x = np.array(points)[:, 0]
        y = np.array(points)[:, 1]
    ## coordinates of the barycenter
    x_m = np.mean(x)
    y_m = np.mean(y)


    def calc_R(xc, yc):
        """ calculate the distance of each 2D points
            from the center (xc, yc) """
        return np.sqrt((x-xc)**2 + (y-yc)**2)

    def f_2(c):
        """ calculate the algebraic distance between
        the data points and the mean circle centered at c=(xc, yc) """
        Ri = calc_R(*c)
        return Ri - Ri.mean()

    center_estimate = x_m, y_m #First guess of the center
    center_2, ier = optimize.leastsq(f_2, center_estimate)

    xc_2, yc_2 = center_2
    Ri_2 = calc_R(*center_2) #Get the center
    R_2  = Ri_2.mean()

    return xc_2, yc_2, R_2

def plot_circles(data, points, vmin=-5000, vmax=10000):
    '''Adds a plot of circles to a given data-array'''
    from matplotlib import pyplot as plt
    data[data>=vmin] = np.nan
    data[data<=vmax] = np.nan
    fig = plt.figure()
    ax=fig.add_subplot(111)
    ax.invert_yaxis()
    X,Y = np.arange(0,data.shape[-1]+1), np.arange(0,data.shape[0]+1)
    ax.pcolormesh(X,Y, data)
    theta_fit = np.linspace(-np.pi, np.pi, 180)
    for quad, pnt in points.items():
        x,y, c_x, c_y, r = fit_circle(pnt)
        ax.scatter(x,y,s=20)
        x_fit2 = c_x + r*np.cos(theta_fit)
        y_fit2 = c_y + r*np.sin(theta_fit)
        plt.plot(x_fit2, y_fit2, linestyle='--', lw=2)
    plt.show()

