from random import randint, random, uniform, choice
from .problem import Problem
from .population import Population
from .algorithm_genetic import GeneralEvolutionaryAlgorithm
from .operators import SwarmStep, DummySelector, RandomGenerator, SwarmStepTVIW, PmMutator, ParetoDominance, \
    EpsilonDominance, crowding_distance
from .archive import Archive
from copy import copy
import time
import math


class SwarmAlgorithm(GeneralEvolutionaryAlgorithm):

    def __init__(self, problem: Problem, name="General Swarm-based Algorithm"):
        super().__init__(problem, name)
        # self.options.declare(name='v_max', default=, lower=0., desc='maximum_allowed_speed')
        self.global_best = None  # swarm algorithms share the information, who is the leader
        self.dominance = ParetoDominance()  # some dominance should be defined for every kind of multi-opbjective swarm

    def init_pvelocity(self, population):
        pass

    def init_pbest(self, population):
        for individual in population:
            individual.features['best_cost'] = individual.costs_signed
            individual.features['best_vector'] = individual.vector

    def khi(self, c1: float, c2: float) -> float:
        """
        Constriction coefficient [1].
        [1] Ebarhart and Kennedym Empirical study of particle swarm optimization,” in Proc. IEEE Int. Congr.
        Evolutionary Computation, vol. 3, 1999, pp. 101–106.

        :param c1: specific parameter to control the particle best component.
        :param c2: specific parameter to control the global best component.
        :return: float, constriction coefficient
        """
        rho = c1 + c2
        if rho <= 4:
            result = 1.0
        else:
            result = 2.0 / (2.0 - rho - (rho ** 2.0 - 4.0 * rho) ** 0.5)

        return result

    def speed_constriction(self, velocity, u_bound, l_bound) -> float:
        """
        Velocity constriction factor [1].

        .. Ref:
        [1] Nebro, Antonio J., et al. "SMPSO: A new PSO-based metaheuristic for multi-objective optimization."
            2009 IEEE Symposium on Computational Intelligence in Multi-Criteria Decision-Making (MCDM). IEEE, 2009.

        :param velocity: parameter velocity for the i^th component
        :param ub: upper bound
        :param lb: lower bound
        :return:
        """

        delta_i = (u_bound - l_bound) / 2.
        # user defined max speed
        velocity = min(velocity, delta_i)
        velocity = max(velocity, -delta_i)

        return velocity

    def select_global_best(self):
        pass

    def inertia_weight(self):
        pass

    def update_global_best(self, offsprings):
        pass

    def update_velocity(self, population):
        pass

    def update_position(self, population):
        pass

    def update_particle_best(self, population):
        for particle in population:
            flag = self.dominance.compare(particle.costs_signed, particle.features['best_cost'])
            if flag != 2:
                particle.features['best_cost'] = particle.costs_signed
                particle.features['best_vector'] = particle.vector

    def turbulence(self, population):
        pass

    def step(self, population):
        self.update_velocity(population)
        self.update_position(population)
        self.turbulence(population)

        offsprings = copy(population)

        # self.evaluator.evaluate(offsprings)
        self.evaluate(offsprings.individuals)
        # self.add_features(offsprings) -- do not reset

        self.update_particle_best(offsprings)
        self.update_global_best(offsprings.individuals)
        return offsprings

    def run(self):
        pass


class OMOPSO(SwarmAlgorithm):
    """
    Implementation of OMOPSO, a multi-objective particle swarm optimizer (MOPSO).
    OMOPSO uses Crowding distance, Mutation and ε-Dominance.
    According to [3], OMOPSO is one of the top-performing PSO algorithms.

    [1] Margarita Reyes SierraCarlos A. Coello Coello
        Improving PSO-Based Multi-objective Optimization Using Crowding, Mutation and ∈-Dominance
        DOI https://doi.org/10.1007/978-3-540-31880-4_35
    [2] S. Mostaghim ; J. Teich :
        Strategies for finding good local guides in multi-objective particle swarm optimization (MOPSO)
        DOI: 10.1109/SIS.2003.1202243
    [3] Durillo, J. J., J. Garcia-Nieto, A. J. Nebro, C. A. Coello Coello, F. Luna, and E. Alba (2009).
        Multi-Objective Particle Swarm Optimizers: An Experimental Comparison.
        Evolutionary Multi-Criterion Optimization, pp. 495-509
    """

    def __init__(self, problem: Problem, name="Particle Swarm Algorithm"):
        super().__init__(problem, name)
        self.options.declare(name='prob_mutation', default=0.2, lower=0,
                             desc='prob_mutation'),
        self.options.declare(name='epsilons', default=0.01, lower=1e-6,
                             desc='prob_epsilons')
        self.n = self.options['max_population_size']
        self.mutator = SwarmStep(self.problem.parameters)
        # self.selector = DummySelector(self.problem.parameters, self.problem.signs)
        self.dominance = ParetoDominance()
        self.features = {'velocity': [],
                         'best_cost': [],  # stores the
                         'best_vector': []}  #
        # set random generator
        self.generator = RandomGenerator(self.problem.parameters)
        self.leaders = Archive()
        self.problem.archive = Archive(dominance=EpsilonDominance(epsilons=self.options['epsilons']))

        # constants for the speed and the position calculation
        self.c1_min = 1.5
        self.c1_max = 2.0
        self.c2_min = 1.5
        self.c2_max = 2.0
        self.r1_min = 0.0
        self.r1_max = 1.0
        self.r2_min = 0.0
        self.r2_max = 1.0
        self.min_weight = 0.1
        self.max_weight = 0.5

        # in this algorithm a polynomial mutation used as a turbulence operator
        self.mutator = PmMutator(self.problem.parameters, self.options['prob_mutation'])

    def inertia_weight(self):
        return uniform(self.min_weight, self.max_weight)

    def init_pvelocity(self, population):
        """
        Inits the particle velocity and its allowed maximum speed.
        :param population: list of individuals
        :return
        """
        for individual in population.individuals:
            # the initial speed is set to zero
            individual.features['velocity'] = [0] * len(individual.vector)

            # for parameter in self.parameters:
            #     delta_i = (parameter['bounds'][1] - parameter['bounds'][0]) / 2.
            #     if parameter['v_max']:
            #         delta_i = min(parameter['v_max'], delta_i)
            #     individual.features['max_speed'] = delta_i
        return

    def turbulence(self, population):
        for i in range(len(population)):
            mutated = self.mutator.mutate(population[i])
            population[i].vector = copy(mutated.vector)

    def update_velocity(self, population):

        for individual in population:

            individual.features['velocity'] = [0] * len(individual.vector)
            global_best = self.select_global_best()

            r1 = round(uniform(self.r1_min, self.r1_max), 1)
            r2 = round(uniform(self.r2_min, self.r2_max), 1)
            c1 = round(uniform(self.c1_min, self.c1_max), 1)
            c2 = round(uniform(self.c2_min, self.c2_max), 1)

            for i in range(0, len(individual.vector)):
                momentum = self.inertia_weight() * individual.vector[i]
                v_cog = c1 * r1 * (individual.features['best_vector'][i] - individual.vector[i])
                v_soc = c2 * r2 * (global_best.vector[i] - individual.vector[i])

                v = self.khi(c1, c2) * (momentum + v_cog + v_soc)
                individual.features['velocity'][i] = self.speed_constriction(v, self.parameters[i]['bounds'][1],
                                                                             self.parameters[i]['bounds'][0])

    def update_position(self, population):

        for individual in population:
            for parameter, i in zip(self.parameters, range(len(individual.vector))):
                individual.vector[i] = individual.vector[i] + individual.features['velocity'][i]

                # adjust maximum position if necessary
                if individual.vector[i] > parameter['bounds'][1]:
                    individual.vector[i] = parameter['bounds'][1]
                    individual.features['velocity'][i] *= -1

                # adjust minimum position if necessary
                if individual.vector[i] < parameter['bounds'][0]:
                    individual.vector[i] = parameter['bounds'][0]
                    individual.features['velocity'][i] *= -1

    def update_global_best(self, swarm):
        """ Manages the leader class in OMOPSO. """

        # the fitness of the particles are calculated by their crowding distance
        crowding_distance(swarm)

        for particle in swarm:
            # because the two archive can be very different
            self.leaders.add(particle)
            self.problem.archive.add(particle)

        # the length of the leaders archive cannot be longer than the number of the initial population
        self.leaders.truncate(self.population_size, 'crowding_distance')

        return

    def select_global_best(self):
        """
        There are different possibilities to select the global best solution.
        The leader class in this concept contains everybody after the initialization, every individual expected as a
        leader, we select 2 from them and select the non-dominated as the global best.

        :return:
        """

        if self.leaders.size() == 1:
            return self.leaders.rand_choice()

        candidates = self.leaders.rand_sample(2)

        # randomly favourize one of them
        best_global = choice(candidates)

        # if one of them dominates, it will be selected as global best
        dom = ParetoDominance.compare(candidates[0], candidates[1])

        if dom == 1:
            best_global = candidates[0]

        if dom == 2:
            best_global = candidates[1]

        self.global_best = copy(best_global)
        return best_global

    def run(self):

        t_s = time.time()
        self.problem.logger.info("PSO: {}/{}".format(self.options['max_population_number'],
                                                     self.options['max_population_size']))
        # initialize the swarm
        self.generator.init(self.options['max_population_size'])
        population = self.gen_initial_population()
        self.evaluate(population.individuals)
        self.add_features(population.individuals)

        self.init_pvelocity(population)
        self.init_pbest(population)
        self.update_global_best(population.individuals)

        i = 0
        while i < self.options['max_population_number']:
            self.update_velocity(population.individuals)
            self.update_position(population.individuals)
            self.turbulence(population.individuals)

            offsprings = copy(population.individuals)

            # self.evaluator.evaluate(offsprings)
            self.evaluate(offsprings)
            # self.add_features(offsprings) -- do not reset
            population = Population(offsprings)
            self.problem.populations.append(population)

            self.update_particle_best(offsprings)
            self.update_global_best(offsprings)

            # population = self.step(population)

        t = time.time() - t_s
        self.problem.logger.info("PSO: elapsed time: {} s".format(t))


# ........................
#
# ........................

class PSO_V1(SwarmAlgorithm):
    """

    X. Li. A Non-dominated Sorting Particle Swarm Optimizer for Multiobjective
    Optimization. In Genetic and Evolutionary Computation - GECCO 2003, volume
    2723 of LNCS, pages 37–48, 2003.

    This algorithm is a variant of the original PSO, published by Eberhart(2000), the origin of this modified algorithm,
    which constriction factor was introduced by Clercs in 1999.

    The code is based on SHI and EBERHARTS algorithm.

    Empirical study of particle swarm optimization,” in Proc. IEEE Int. Congr. Evolutionary Computation, vol. 3,
    1999, pp. 101–106.
    """

    def __init__(self, problem: Problem, name="Particle Swarm Algorithm - with time varieting inertia weight"):
        super().__init__(problem, name)
        self.n = self.options['max_population_size']
        self.mutator = SwarmStepTVIW(self.problem.parameters, self.options['max_population_number'])
        self.selector = DummySelector(self.problem.parameters, self.problem.signs)

    def run(self):
        # set random generator
        self.generator = RandomGenerator(self.problem.parameters)
        self.generator.init(self.options['max_population_size'])

        population = self.gen_initial_population()
        self.evaluate(population.individuals)
        self.add_features(population.individuals)

        for individual in population.individuals:
            self.mutator.evaluate_best_individual(
                individual)  # TODO: all evaluating should be derived from Evaluator class

        self.selector.fast_nondominated_sorting(population.individuals)
        self.problem.populations.append(population)

        t_s = time.time()
        self.problem.logger.info("PSO: {}/{}".format(self.options['max_population_number'],
                                                     self.options['max_population_size']))

        i = 0
        while i < self.options['max_population_number']:
            offsprings = self.selector.select(population.individuals)

            pareto_front = []
            for individual in offsprings:
                if individual.features['front_number'] == 1:
                    pareto_front.append(individual)

            for individual in offsprings:
                index = randint(0, len(pareto_front) - 1)  # takes random individual from Pareto front
                best_individual = pareto_front[index]
                if best_individual is not individual:
                    self.mutator.update(best_individual)
                    self.mutator.mutate(individual)

            self.evaluate(offsprings)
            self.add_features(offsprings)

            for individual in offsprings:
                self.mutator.evaluate_best_individual(individual)

            self.selector.fast_nondominated_sorting(offsprings)
            population = Population(offsprings)
            self.problem.populations.append(population)

            i += 1

        t = time.time() - t_s
        self.problem.logger.info("PSO: elapsed time: {} s".format(t))
