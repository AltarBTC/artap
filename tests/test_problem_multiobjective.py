from unittest import TestCase, main
from context import Problem
from context import GeneticAlgorithm
from scipy.optimize import minimize


class MyProblem(Problem):
    """ Describe simple one obejctive optimization problem. """
    def __init__(self, name):
        self.max_population_number = 3
        self.max_population_size = 3
        self.parameters = {'x_1': 10, 'x_2': 10, 'x_3': 10}
        self.costs = ['F_1', 'F_2']

        super().__init__(name, self.parameters, self.costs)

    def eval(self, x):
        F1 = 0
        F2 = 0
        
        for i in x:
            F1 += i*i        
        
        F2 = -(abs(x[0] - x[1]) + abs(x[1] - x[2])  + abs(x[2] - x[1]))
        return [F1, F2]

class TestSimpleOptimization(TestCase):
    """ Tests simple one objective optimization problem."""
    
    def test_upper(self):   
        problem = MyProblem("LocalPythonProblem")        
        algorithm = GeneticAlgorithm(problem)
        algorithm.run()        


if __name__ == '__main__':
    main()
    

