'''
Created on Mar 7, 2011

@author: johnsalvatier
''' 
from numpy import floor
from numpy.linalg import solve
from scipy.linalg import cholesky, cho_solve


from utils import *
from ..core import * 


# todo : 
#make step method use separate gradient and logp functions
#add constraint handling via page 37 of Radford's http://www.cs.utoronto.ca/~radford/ham-mcmc.abstract.html
#allow users to pass Hamiltonian splitting functions

def hmc_step(model, vars, C, step_size_scaling = .25, trajectory_length = 2., is_cov = False):
    n = C.shape[0]
    
    logp_d_dict = model_logp_dlogp(model, vars)
    
    step_size = step_size_scaling * n**(1/4.)
    
    pot = quad_potential(C, is_cov)

    def step(logp_d, state, q0):
        
        if state is None:
            state = SamplerHist()
            
        #randomize step size
        e = uniform(.85, 1.15) * step_size
        nstep = int(floor(trajectory_length / step_size))
        
        q = q0
        logp0, dlogp = logp_d(q)
        logp = logp0
        
        p = p0 = pot.random()
        
        #use the leapfrog method
        p = p - (e/2) * -dlogp # half momentum update
        
        for i in range(nstep): 
            #alternate full variable and momentum updates
            q = q + e * pot.velocity(p)
             
            logp, dlogp = logp_d(q)
            
            if i != nstep - 1:
                p = p - e * -dlogp
             
        p = p - (e/2) * -dlogp  # do a half step momentum update to finish off
        
        p = -p 
            
        # - H(q*, p*) + H(q, p) = -H(q, p) + H(q0, p0) = -(- logp(q) + K(p)) + (-logp(q0) + K(p0))
        mr = (-logp0) + pot.energy(p0) - ((-logp)  + pot.energy(p))
        state.metrops.append(mr)
        
        return state, metrop_select(mr, q, q0)
        
    return array_step(step, logp_d_dict, vars)



def quad_potential(C, is_cov):
    if is_cov:
        return QuadPotential(C)
    else :
        return QuadPotential_Inv(C) 

class QuadPotential_Inv(object):
    def __init__(self, A):
        self.L = cholesky(A, lower = True)
        
    def velocity(self, x ):
        return cho_solve((self.L, True), x)
        
    def random(self):
        n = normal(size = self.L.shape[0])
        return dot(self.L, n)
    
    def energy(self, x):
        L1x = solve(self.L, x)
        return .5 * dot(L1x.T, L1x)


class QuadPotential(object):
    def __init__(self, A):
        self.A = A
        self.L = cholesky(A, lower = True)
    
    def velocity(self, x):
        return dot(self.A, x)
    
    def random(self):
        n = normal(size = self.L.shape[0])
        return solve(self.L.T, n)
    
    def energy(self, x):
        return .5 * dot(x, dot(self.A, x))
        