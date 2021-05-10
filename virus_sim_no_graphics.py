import math
import numpy as np
import numpy.random as rnd
import matplotlib.pyplot as plt

def distance(x1, x2, y1, y2):
    return np.sqrt((y2-y1)**2+(x2-x1)**2)


class Person:
    def __init__(self, x, y, v, phi, om, state, tp_spot, tp_radius, death_risk, vaccination_rate):
        self.x = x
        self.y = y
        self.vel = v
        self.angle = phi
        self.rot_vel = om
        self.state = state
        self.current_sick_time = 0
        self.sick_time = rnd.normal(300, 50)
        self.tp_chance = 0.01
        self.tp_cooldown = 15
        self.tp_time = 0
        self.tp_back_cooldown = 15
        self.tp_spot = tp_spot
        self.tp_radius = tp_radius
        self.tpd = False
        self.last_pos = [self.x, self.y]
        self.matrix_pos = [0,0]
        self.death_risk = death_risk
        self.vaccination_rate = vaccination_rate

    def update(self, area):
        if self.state != 3:
            #self.teleport()

            #Stega framåt
            self.x += self.vel * np.cos(self.angle)
            self.y += self.vel * np.sin(self.angle)

            #Se till att individerna inte får gå utanför området
            if not area.width > self.x > 0 or not area.height > self.y > 0:
                self.angle += np.pi
                if self.x < 0:
                    self.x = 0
                if self.x > area.width:
                    self.x = area.width
                if self.y < 0:
                    self.y = 0
                if self.y > area.height:
                    self.y = area.height

            #Rotera slumpmässigt
            self.angle += rnd.choice([-1, 1])*rnd.random()*self.rot_vel

            #Vad händer när man är infekterad?
            if self.state == 1:
                self.current_sick_time += 1
                r = rnd.random()
                if r < self.death_risk:
                    self.state = 3
                    return -1
            #Chans till vaccin
            if self.state == 0:
                r = rnd.random()
                if r<self.vaccination_rate:
                    self.state = 4
                    return 4

            #Tillfriskning
            if self.current_sick_time >= self.sick_time and self.state != 2:
                self.state = 2
                return 1
        return 0

    def teleport(self):
        if not self.tpd:
            R = rnd.random()
            if R < self.tp_chance and self.tp_time >= self.tp_cooldown:
                self.last_pos = [self.x, self.y]
                r = rnd.rand()*self.tp_radius
                theta = rnd.random()*2*np.pi
                tp_x = self.tp_spot[0] + r * np.cos(theta)
                tp_y = self.tp_spot[1] + r * np.sin(theta)
                self.x = tp_x
                self.y = tp_y
                self.tp_time = 0
                self.tpd = True
            else:
                self.tp_time += 1
        else:
            if self.tp_time >= self.tp_back_cooldown:
                self.x = self.last_pos[0]
                self.y = self.last_pos[1]
                self.tpd = False
                self.tp_time = 0
            else:
                self.tp_time += 1

class PopulationMatrix: #skapar matris för avståndsbedömning
    def __init__(self, area, safe_distance):
        self.mat_pop = []
        self.area = area
        self.safe_distance = safe_distance
        self.width = math.ceil(area.width//safe_distance)
        self.height = math.ceil(area.height//safe_distance)
        for i in range(self.width):
            self.mat_pop.append([])
            for j in range(self.height):
                self.mat_pop[i].append([])

    def add_pop(self, pop_list): #lägger in pop i matrisen
        for person in pop_list:
            self.add_person(person)

    def add_person(self,person): #lägger till en person i matrisen
        person.mat_pos = [math.floor(person.x//self.safe_distance), math.floor(person.y//self.safe_distance)]
        if person.mat_pos[0] > self.width-1:
            person.mat_pos[0] = self.width-1
        if person.mat_pos[1] > self.height-1:
            person.mat_pos[1] = self.height-1
        self.mat_pop[person.mat_pos[0]][person.mat_pos[1]].append(person)

    def update_person(self, person): #uppdaterar personens matrix pos efter att positionen har ändrats
        self.mat_pop[person.mat_pos[0]][person.mat_pos[1]].remove(person)
        person.mat_pos = [person.x//self.safe_distance, person.y//self.safe_distance]
        self.add_person(person)

    def check_distance(self,pop): #returnernar ett set med par med folk som är för nära varandra
        too_close = set()
        for person in pop:
            matrix_pos = person.mat_pos
            for i in range(matrix_pos[0] - 1, min(self.width, matrix_pos[0] + 2)):
                for j in range(matrix_pos[1] - 1, min(self.height, matrix_pos[1] + 2)):
                    if len(self.mat_pop[i][j]) != 0:
                        for person_2 in self.mat_pop[i][j]:
                            if distance(person.x, person_2.x, person.y, person_2.y) < self.safe_distance:
                                too_close.add((person, person_2))
        return too_close


class Population:
    def __init__(self, n, area, standard_distance, standard_velocity, infected_ratio, death_risk, vaccination_rate):
        self.size = 0
        self.distribution = {}
        self.distribution["Susceptible"] = 0
        self.distribution["Infected"] = 0
        self.distribution["Recovered"] = 0
        self.distribution["Dead"] = 0
        self.distribution["Vaccinated"] = 0
        self.population_list = []
        self.area = area
        self.distance = standard_distance/n**(1/2)
        self.death_risk = death_risk
        self.vaccination_rate = vaccination_rate
        print(self.distance)
        self.population_matrix = PopulationMatrix(self.area, self.distance)
        self.vel = standard_velocity/n**(1/2)
        self.rot_vel = np.pi/15
        inf = math.ceil(max(1, n*infected_ratio))
        for i in range(n-inf):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 0)
        for i in range(inf):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 1)


    def add_person(self, x, y, sick):
        p = Person(x, y, self.vel, 2 * np.pi * rnd.random(), self.rot_vel, sick, self.area.tp_spot, self.area.tp_radius, self.death_risk, self.vaccination_rate)
        self.population_list.append(p)
        self.population_matrix.add_person(p)
        self.size += 1
        if sick:
            self.distribution["Infected"] += 1
        else:
            self.distribution["Susceptible"] += 1


    def size(self):
        return len(self.population_list)


class Area:
    def __init__(self, x, y, w, h, tp_spot, radius, n):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.tp_spot = tp_spot
        self.tp_radius = radius


class Manager:
    def __init__(self, population, inf_prob):
        self.population = population
        self.inf_prob = inf_prob
        self.distance = self.population.distance
        self.colors = [(0,0,0),(255,0,0),(0,0,255),(100,100,100),(127,0,255)]

    def update(self, population):

        #Undersöker om smittspridning kan ske
        close_persons = population.population_matrix.check_distance(population.population_list)
        for pair in close_persons:
            if (pair[0].state == 1 and pair[1].state == 0):
                if rnd.random()<self.inf_prob:
                    self.infect(pair[1])

            elif (pair[0].state == 0 and pair[1].state == 1):
                if rnd.random()<self.inf_prob:
                    self.infect(pair[0])

        for person in population.population_list:
            #Kör update för varje person
            state = person.update(population.area)
            self.population.population_matrix.update_person(person)
            if state == 1:
                population.distribution["Infected"] -= 1
                population.distribution["Recovered"] += 1
            elif state == -1:
                population.distribution["Infected"] -= 1
                population.distribution["Dead"] += 1
            elif state == 4:
                self.vaccinate(person)

    def infect(self, person):
        self.population.distribution["Susceptible"] -= 1
        self.population.distribution["Infected"] += 1
        person.state = 1
    def vaccinate(self, person):
        self.population.distribution["Susceptible"] -= 1
        self.population.distribution["Vaccinated"] += 1
        person.state = 4


class Stats:
    def __init__(self, pop, colors):
        self.population = pop
        self.data = {}
        for key in self.population.distribution.keys():
            self.data[key] = []
        self.colors = colors
        self.done = False

    def update(self):
        for key in self.population.distribution.keys():
            self.data[key].append(self.population.distribution[key])
        if self.data["Infected"][-1] <= 0 and self.done == False:
            self.done = True
            for i, key in enumerate(self.data.keys()):
                clr = self.colors[i]
                plt.plot(self.data[key], color=(clr[0]/255,clr[1]/255,clr[2]/255))
            plt.legend(self.data.keys())
            plt.show()
        return self.done

    def current_stats(self):
        s = ""
        for key in self.data.keys():
            s += key + ": " + str(self.data[key][-1]) + "\n"
        return s


def main():
    n = int(input("Population size: "))
    infected = float(input("Part of population infected in the beginning (for example 0.01): "))
    inf_prob = float(input("Infection probability (every frame, 0.01 is pretty lagom): "))
    death_risk = float(input("Death probability (every frame, 0.00005 is pretty lagom): "))
    vaccination_rate = float(input("Vaccination rate (every frame, 0.001 is pretty lagom: "))
    std_distance = 350
    std_velocity = 14
    area = Area(100, 150, 600, 400, [200,200], 50, n)
    population = Population(n, area, std_distance, std_velocity, infected, death_risk, vaccination_rate)
    manager = Manager(population, inf_prob)
    stats = Stats(population, manager.colors)
    #Huvudloop där allt uppdateras
    frames = 0
    while True:
        manager.update(population)
        done = stats.update()
        if done:
            pygame.quit()
            break
        frames += 1
        if frames % 15 == 0:
            print("Time (frames): " + str(frames))
            print(stats.current_stats())

main()