from .problem import Problem
from .algorithm import Algorithm
from .population import Population, Population_NSGA_II
from .individual import Individual_NSGA_II, Individual

from abc import ABCMeta, abstractmethod
import random

class GeneralEvolutionaryAlgorithm(Algorithm):
    """ Basis Class for evolutionary algorithms """

    def __init__(self, problem: Problem, name="General Evolutionary Algorithm"):
        super().__init__(problem, name)
        self.problem = problem

    def gen_initial_population(self):
        pass

    def select(self):
        pass

    def form_new_population(self):
        pass

    def run(self):
        pass


class GeneticAlgorithm(GeneralEvolutionaryAlgorithm):

    def __init__(self, problem: Problem, name="General Evolutionary Algorithm"):
        super().__init__(problem, name)
        self.population_size = self.problem.max_population_size
        self.parameters_length = len(self.problem.parameters)
        self.populations_number = self.problem.max_population_count
        self.current_population = 0

    def gen_initial_population(self):
        population = Population(self.problem)
        population.gen_random_population(self.population_size, self.parameters_length, self.problem.parameters)
        population.evaluate()

        self.problem.add_population(population)

        self.current_population += 1
        return population

    def select(self):
        pass

    def form_new_population(self):
        pass

    def run(self):
        pass


class NSGA_II(GeneticAlgorithm):

    def __init__(self, problem: Problem, name="NSGA_II Evolutionary Algorithm"):
        super().__init__(problem, name)
        self.prob_cross = 0.6
        self.prob_mutation = 0.05

    def gen_initial_population(self):
        population = Population_NSGA_II(self.problem)
        population.gen_random_population(self.population_size, self.parameters_length, self.problem.parameters)
        self.problem.populations.append(population)

    def is_dominate(self, p, q):
        dominate = False
        for i in range(0, len(self.problem.costs)):
            if p.costs[i] > q.costs[i]:
                return False
            if p.costs[i] < q.costs[i]:
                dominate = True

        # TODO: Constrains
        # for i in range(0,len(p.violation)):
        #    if p.violation[i] > q.violation[i] :
        #        return False
        #    if p.violation[i] < q.violation[i] :
        #        dominate = True

        return dominate

    def crossover(self):
        pass

    def mutate(self):
        pass

    def fast_non_dominated_sort(self, population):
        pareto_front = []
        front_number = 1

        for p in population:
            for q in population:
                if p is q:
                    continue
                if self.is_dominate(p, q):
                    p.dominate.add(q)
                elif self.is_dominate(q, p):
                    p.domination_counter = p.domination_counter + 1

            if p.domination_counter == 0:
                p.front_number = front_number
                pareto_front.append(p)

        while not len(pareto_front) == 0:
            front_number += 1
            temp_set = []
            for p in pareto_front:
                for q in p.dominate:
                    q.domination_counter -= 1
                    if q.domination_counter == 0 and q.front_number == 0:
                        q.front_number = front_number
                        temp_set.append(q)
            pareto_front = temp_set

    # TODO: faster algorithm
    @staticmethod
    def sort_by_coordinate(population, dim):
        # individuals = population.individuals.copy()
        individuals = population

        for i in range(0, len(individuals) - 1):
            for j in range(i + 1, len(individuals)):
                if individuals[i].parameters[dim] < individuals[j].parameters[dim]:
                    temp = individuals[i]
                    individuals[i] = individuals[j]
                    individuals[j] = temp

        return individuals

    def calculate_crowd_dis(self, population):
        infinite = float("inf")

        for dim in range(0, len(self.problem.parameters)):
            new_list = self.sort_by_coordinate(population, dim)

            new_list[0].crowding_distance += infinite
            new_list[-1].crowding_distance += infinite
            max_distance = new_list[0].parameters[dim] - new_list[-1].parameters[dim]
            for i in range(1, len(new_list) - 1):
                distance = new_list[i - 1].parameters[dim] - new_list[i + 1].parameters[dim]
                if max_distance == 0:
                    new_list[i].crowding_distance = 0
                else:
                    new_list[i].crowding_distance += distance / max_distance

        for p in population:
            p.crowding_distance = p.crowding_distance / len(self.problem.parameters)

    @staticmethod
    def tournament_select(parents, part_num=2):  # binary tournament selection
        participants = random.sample(parents, part_num)
        best = participants[0]
        best_rank = participants[0].front_number
        best_crowding_distance = participants[0].crowding_distance

        for p in participants[1:]:
            if p.front_number < best_rank or \
                    (p.front_number == best_rank and p.crowding_distance > best_crowding_distance):
                best = p
                best_rank = p.front_number
                best_crowding_distance = p.crowding_distance

        return best

    def generate(self, parents):
        # generate two children from two parents

        children = []
        while len(children) < self.population_size:
            parent1 = self.tournament_select(parents)
            parent2 = self.tournament_select(parents)
            while parent1 == parent2:
                parent2 = self.tournament_select(parents)

            child1, child2 = self.cross(parent1, parent2)
            child1 = self.mutation(child1)
            child2 = self.mutation(child2)

            children.append(child1)
            children.append(child2)
        return children

    def cross(self, p1, p2):  # the random linear operator
        if random.uniform(0, 1) >= self.prob_cross:
            return p1, p2

        parameter1, parameter2 = [], []
        linear_range = 2
        alpha = random.uniform(0, linear_range)
        for j in range(0, len(p1.parameters)):
            parameter1.append(alpha * p1.parameters[j] +
                              (1 - alpha) * p2.parameters[j])
            parameter2.append((1 - alpha) * p1.parameters[j] +
                              alpha * p2.parameters[j])
        c1 = Individual_NSGA_II(parameter1, self.problem)
        c2 = Individual_NSGA_II(parameter2, self.problem)
        return c1, c2

    def mutation(self, p):  # uniform random mutation
        mutation_space = 0.1
        parameters = []
        i = 0
        for parameter in self.problem.parameters.items():
            if random.uniform(0, 1) < self.prob_mutation:
                para_range = mutation_space * (parameter[1]['bounds'][0] - parameter[1]['bounds'][1])
                mutation = random.uniform(-para_range, para_range)
                parameters.append(p.parameters[i] + mutation)
            else:
                parameters.append(p.parameters[i])
            i += 1

        p_new = Individual_NSGA_II(parameters, self.problem)
        return p_new

    def select(self):
        pass

    def form_new_population(self):
        pass

    def run(self):

        self.gen_initial_population()
        parent_individuals = self.problem.populations[0].individuals
        child_individuals = []

        for it in range(self.problem.max_population_count):

            individuals = parent_individuals + child_individuals

            Population.evaluate_individuals(individuals, self.problem)

            self.fast_non_dominated_sort(individuals)
            self.calculate_crowd_dis(individuals)

            parents = []
            front = 1

            while len(parents) < self.population_size:
                for individual in individuals:
                    if individual.front_number == front:
                        parents.append(individual)
                        if len(parents) == self.population_size:
                            break
                front = front + 1

            population = Population_NSGA_II(self.problem, individuals)
            self.problem.add_population(population)
            self.current_population += 1

            child_individuals = self.generate(parent_individuals)