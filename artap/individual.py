from random import random, uniform
from numpy.random import normal
from abc import *

# from multiprocessing import Queue
# from numpy import NaN
# from copy import copy

# import itertools


class Individual(metaclass=ABCMeta):
    """
       Collects information about one point in design space.
    """
    number = 0
    results = None
    gradients = None

    def __init__(self, design_parameters, problem, population_id=0):
        # self.parameters = design_parameters.copy()
        self.parameters = design_parameters
        self.problem = problem
        self.length = len(self.parameters)
        self.costs = []
        self.number = Individual.number
        self.gradient = []
        Individual.number += 1

        self.feasible = 0.0  # the distance from the feasibility region in min norm
        self.population_id = population_id
        self.is_evaluated = False
        self.dominate = set()
        self.domination_counter = 0
        self.front_number = 0
        self.crowding_distance = 0

        # For particle swarm optimization
        self.velocity_i = []  # particle velocity
        self.pos_best_i = []  # best position individual
        self.err_best_i = -1  # best error individual
        self.err_i = -1  # error individual

        for i in range(0, len(self.parameters)):
            self.velocity_i.append(uniform(-1, 1))

    def __repr__(self):
        """ :return: [parameters[p1, p2, ... pn]; costs[c1, c2, ... cn]] """
        string = "parameters: ["

        for i, number in enumerate(self.parameters):
            string += str(number)
            if i < len(self.costs)-1:
                string += ", "

        string = string[:len(string) - 1]
        string += "]"
        string += "; costs:["
        for i,number in enumerate(self.costs):
            string += str(number)
            if i < len(self.costs)-1:
                string += ", "
        string += "]\n"
        return string

    def to_list(self):
        params = [[self.number], [self.population_id], self.parameters, self.costs]
        # flatten list
        out = [val for sublist in params for val in sublist]
        out.append(self.front_number)
        if self.crowding_distance == float('inf'):
            out.append(0)
        else:
            out.append(self.crowding_distance)
        if self.feasible == float('inf'):
            out.append(0)
        else:
            out.append(self.feasible)
        dominates = []
        for individual in self.dominate:
            dominates.append(individual.number)
        out.append(dominates)
        out.append(self.gradient)
        return out

    def evaluate(self):
        # check the constraints
        constraints = self.problem.eval_constraints(self.parameters)

        if constraints:
            self.feasible = sum(map(abs, constraints))

        # problem cost function evaluate only in that case when the problem is fits the constraints
        # TODO: find better solution for surrogate
        if self.problem.surrogate:
            costs = self.problem.evaluate_surrogate(self.parameters)
        else:
            # increase counter
            self.problem.eval_counter += 1
            # eval
            costs = self.problem.eval(self.parameters)

        if type(costs) is not list:
            self.costs = [costs]
        else:
            self.costs = costs
        # scipy uses the result number, the genetic algorithms using the property value
        self.is_evaluated = True
        if self.problem.options['save_level'] == "individual":
            self.problem.data_store.write_individual(self.to_list())

        if self.problem.options['max_processes'] > 1:
            if Individual.results is not None:
                Individual.results.put([self.number, costs, self.feasible])

        return costs  # for scipy

    def evaluate_gradient(self):
        self.gradient = self.problem.evaluate_gradient(self)
        if self.problem.options['max_processes'] > 1:
            if Individual.results is not None:
                Individual.results.put([self.number, self.gradient])

        return self.gradient

    def set_id(self):
        self.number = Individual.number
        Individual.number += 1


    @classmethod
    def gen_individuals(cls, number, problem, population_id):
        individuals = []
        for i in range(number):
            individuals.append(cls.gen_individual(problem, population_id))
        return individuals

    @classmethod
    def gen_individual(cls, problem, population_id=0):
        parameters_vector = cls.gen_vector(cls, problem.parameters)
        return cls(parameters_vector, problem, population_id)

    @staticmethod
    def gen_vector(cls, design_parameters: dict):

        parameters_vector = []
        for parameter in design_parameters.items():

            if not ('bounds' in parameter[1]):
                bounds = [parameter["initial_value"] * 0.5, parameter["initial_value"] * 1.5]
            else:
                bounds = parameter[1]['bounds']

            if not ('precision' in parameter[1]):
                precision = None
            else:
                precision = parameter[1]['precision']

            if (precision is None) and (bounds is None):
                parameters_vector.append(cls.gen_number())
                continue

            if precision is None:
                parameters_vector.append(cls.gen_number(bounds=bounds))
                continue

            if bounds is None:
                parameters_vector.append(cls.gen_number(precision=precision))
                continue

            parameters_vector.append(cls.gen_number(bounds, precision))

        return parameters_vector

    @classmethod
    def gen_number(cls, bounds=None, precision=0, distribution="uniform"):

        number = 0
        if bounds is None:
            bounds = [0, 1]

        if precision == 0:
            precision = 1e-12

        if distribution == "uniform":
            number = random() * (bounds[1] - bounds[0]) + bounds[0]
            number = round(number / precision) * precision

        if distribution == "normal":
            mean = (bounds[0] + bounds[1]) / 2
            std = (bounds[1] - bounds[0]) / 6
            number = normal(mean, std)

        return number
