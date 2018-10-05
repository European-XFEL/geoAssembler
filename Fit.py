from scipy import optimize
import numpy as np
''' A module that porvides multiple fitting methods '''
def countcalls(fn):
    def wrapper(*args, **kwargs):
        wrapper.ncalls += 1
        return fn(*args, **kwargs)
    wrapper.ncalls = 0
    wrapper.__name__ = fn.__name__
    return wrapper



def fit_circle_odr(points):
    from scipy import odr
    '''Least-Square of the data-points to a circle'''
    try:
        x = points.x
        y = points.y
    except (KeyError, ValueError):
        x = np.array(points)[:, 0]
        y = np.array(points)[:, 1]
    def calc_R(c):
        """ calculate the distance of each 2D points from the center c=(xc, yc) """
        return np.sqrt((x-c[0])**2 + (y-c[1])**2)

    @countcalls
    def f_4(beta, x):
        """ implicit function of the circle """
        xc, yc, r = beta
        xi, yi    = x

        return (xi-xc)**2 + (yi-yc)**2 -r**2

    @countcalls
    def jacb(beta, x):
        """ Jacobian function with respect to the parameters beta.
        return df/dbeta
        """
        xc, yc, r = beta
        xi, yi    = x

        df_db    = np.empty((beta.size, x.shape[1]))
        df_db[0] =  2*(xc-xi)                     # d_f/dxc
        df_db[1] =  2*(yc-yi)                     # d_f/dyc
        df_db[2] = -2*r                           # d_f/dr

        return df_db

    @countcalls
    def jacd(beta, x):
        """ Jacobian function with respect to the input x.
        return df/dx
        """
        xc, yc, r = beta
        xi, yi    = x

        df_dx    = np.empty_like(x)
        df_dx[0] =  2*(xi-xc)                     # d_f/dxi
        df_dx[1] =  2*(yi-yc)                     # d_f/dyi

        return df_dx


    def calc_estimate(data):
        """ Return a first estimation on the parameter from the data  """
        xc0, yc0 = data.x.mean(axis=1)
        r0 = np.sqrt((data.x[0]-xc0)**2 +(data.x[1] -yc0)**2).mean()
        return xc0, yc0, r0

    lsc_data  = odr.Data(np.row_stack([x, y]), y=1)
    lsc_model = odr.Model(f_4, implicit=True, estimate=calc_estimate, fjacd=jacd, fjacb=jacb)
    lsc_odr   = odr.ODR(lsc_data, lsc_model)
    lsc_odr.set_job(deriv=3)                    # use user derivatives function without checking
    lsc_out   = lsc_odr.run()

    xc_4, yc_4, R_4 = lsc_out.beta
    Ri_4       = calc_R([xc_4, yc_4])
    residu_4   = np.sum((Ri_4 - R_4)**2)
    residu2_4  = np.sum((Ri_4**2-R_4**2)**2)
    ncalls_4   = f_4.ncalls
    return xc_4, yc_4, R_4, residu_4, ncalls_4

def fit_circle(points):
    '''Least-Square of the data-points to a circle'''
    try:
        x = points.x
        y = points.y
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

    @countcalls
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

    residu2_2  = np.sum((Ri_2**2-R_2**2)**2)
    residu_2  = np.sum((Ri_2**2-R_2**2))
    ncalls_2   = f_2.ncalls
    return xc_2, yc_2, R_2, residu_2, ncalls_2

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

