import unittest

from artap.problem import Problem
from artap.algorithm_bayesopt import BayesOptSerial, BayesOptParallel
from artap.algorithm_bayes import Bayes, BayesianOptimization

from artap.results import Results
from artap.datastore import DummyDataStore
from artap.benchmark_functions import Booth

import numpy as np


# PBOUNDS = {'p1': (-10, 10), 'p2': (-10, 10)}
PBOUNDS = {'x': (-2, 10)}


def target_func(x):
    # val = sum(x)
    # val = -Booth.eval(x)
    val = np.exp(-(x - 2)**2) + np.exp(-(x - 6)**2/10) + 1/ (x**2 + 1)
    # print(val, x)
    return val

class MyProblemOne(Problem):
    """ Describe simple one objective optimization problem. """
    def __init__(self, name):
        parameters = {'x_1': {'initial_value': 2.5, 'bounds': [-2, 10]}}
        costs = ['F']

        super().__init__(name, parameters, costs)

    def evaluate(self, x):
        return -(np.exp(-(x - 2)**2) + np.exp(-(x - 6)**2/10) + 1/ (x**2 + 1))

class MyProblem(Problem):
    """ Describe simple one objective optimization problem. """
    def __init__(self, name):
        parameters = {'x_1': {'initial_value': 2.5, 'bounds': [-10, 10]},
                      'x_2': {'initial_value': 1.5, 'bounds': [-10, 10]}}
        costs = ['F']

        super().__init__(name, parameters, costs)

    def evaluate(self, x):
        return [Booth.eval(x)]


class TestBayesOptOptimization(unittest.TestCase):
    """ Tests simple one objective optimization problem."""

    def xtest_local_problem_bayesopt_parallel(self):
        problem = MyProblem("TestBayesOptParallel")
        algorithm = BayesOptParallel(problem)
        algorithm.options['verbose_level'] = 0
        algorithm.options['n_iterations'] = 100
        algorithm.run()
        # TODO - multiprocess test

        results = Results(problem)
        optimum = results.find_minimum(name='F')
        self.assertAlmostEqual(optimum, 0, places=2)

    def xtest_local_problem_bayesopt_serial(self):
        problem = MyProblem("TestBayesOptSerial")
        algorithm = Bayes(problem)
        algorithm.options['verbose_level'] = 0
        algorithm.options['n_iterations'] = 200
        algorithm.run()

        results = Results(problem)
        optimum = results.find_minimum(name='F')
        self.assertAlmostEqual(optimum, 0, places=2)

    def xtest_local_problem_bayesopt_serial(self):
        problem = MyProblem("TestBayesOptSerial")
        algorithm = BayesOptSerial(problem)
        algorithm.options['verbose_level'] = 0
        algorithm.options['n_iterations'] = 20
        algorithm.run()

        results = Results(problem)
        optimum = results.find_minimum(name='F')
        print(optimum)

    def xtest_local_problem_bayesop_one(self):
        problem = MyProblemOne("TestBayesOptSerial")
        algorithm = BayesOptSerial(problem)
        algorithm.options['verbose_level'] = 0
        algorithm.options['n_iterations'] = 20
        algorithm.run()

        results = Results(problem)
        optimum = results.find_minimum(name='F')
        print(optimum)

    def test_bayesoptimization(self):
        optimizer = BayesianOptimization(f=target_func,
                                         pbounds=PBOUNDS,
                                         random_state=np.random.RandomState(1))

        optimizer.maximize(init_points=5, n_iter=30, acq="ucb", kappa=10.0)
        print("maximum")
        print(optimizer.max)


if __name__ == '__main__':
    unittest.main()