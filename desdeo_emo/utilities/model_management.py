from numpy.core.numeric import indices
from numpy.lib.arraysetops import unique
from pandas.core.frame import DataFrame
from desdeo_tools.scalarization.ASF import SimpleASF, ReferencePointASF
from numba import njit
import numpy as np
import pandas as pd
import copy
from desdeo_problem.surrogatemodels.SurrogateModels import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import DotProduct,\
    WhiteKernel, RBF, Matern, ConstantKernel
from desdeo_problem import MOProblem



#TODO: add @njit function here
def remove_duplicate(
    X: np.ndarray,
    archive_x: np.ndarray
    ):
    """identifiesthe duplicate rows for decision variables
    Args:
    X (np.ndarray): the current decision variables.
    archive_x (np.ndarray): The decision variables in the archive.

    Returns: 
    indicies (np.ndarray): the indicies of solutions that are NOT already in the archive.
    """

    all_variables = np.vstack((archive_x,X))
    all_variables_indicies = np.arange(len(all_variables))

    e,unique_variables_indicies = np.unique(all_variables, return_index=True, axis=0)

    repeated_all_variables = np.delete(all_variables_indicies, unique_variables_indicies)
    repeated_in_X = repeated_all_variables - len(archive_x)
    X_indicies = np.arange(len(X))
    X_uniqe_indicies = np.delete(X_indicies, repeated_in_X)

        
    return X_uniqe_indicies



def ikrvea_mm(
    reference_point: np.ndarray,
    individuals: np.ndarray,
    objectives: np.ndarray,
    uncertainity: np.ndarray,
    problem: MOProblem,
    u: int) -> float:
    """ Selects the solutions that need to be reevaluated with the original functions.
    This model management is based on the following papaer: 

    'P. Aghaei Pour, T. Rodemann, J. Hakanen, and K. Miettinen, “Surrogate assisted interactive
     multiobjective optimization in energy system design of buildings,” 
     Optimization and Engineering, 2021.'

    Args:
        reference_front (np.ndarray): The reference front that the current front is being compared to.
        Should be an one-dimensional array.
        individuals (np.ndarray): Current individuals generated by using surrogate models
        objectives (np.ndarray): Current objectives  generated by using surrogate models
        uncertainity (np.ndarray): Current Uncertainty values generated by using surrogate models
        problem : the problem class

    Returns:
        float: the new problem object that has an updated archive.
    """     
    
    nd = remove_duplicate(individuals, problem.archive.drop(
            problem.objective_names, axis=1).to_numpy()) #removing duplicate solutions
    if len(nd) == 0:
        return problem
    else:
        non_duplicate_dv = individuals[nd]
        non_duplicate_obj = objectives[nd]
        non_duplicate_unc = uncertainity[nd]
        
    # Selecting solutions with lowest ASF values
    asf_solutions = SimpleASF([1]*problem.n_of_objectives).__call__(non_duplicate_obj, reference_point)
    idx = np.argpartition(asf_solutions, 2*u)
    asf_unc = np.max(non_duplicate_unc [idx[0:2*u]], axis= 1)
    # index of solutions with lowest Uncertainty
    lowest_unc_index = np.argpartition(asf_unc, u)[0:u]
    # evaluating the solutions in asf_unc with lowest uncertainty. The archive will get update in problem.evaluate()
    problem.evaluate(non_duplicate_dv[lowest_unc_index], use_surrogate=False)[0] 
    
    problem.train(models=GaussianProcessRegressor,\
         model_parameters={'kernel': Matern(nu=1.5)}) 

    return problem

