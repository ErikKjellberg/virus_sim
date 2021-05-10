import pygame
import math
import numpy as np
import numpy.random as rnd
import matplotlib.pyplot as plt


pygame.init()
font1 = pygame.font.SysFont("courier", 24)
font2 = pygame.font.SysFont("Arial", 12, italic=True, bold=True)
width, height = 1000, 600
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
fps = 15

def distance(x1, x2, y1, y2):
    return np.sqrt((y2-y1)**2+(x2-x1)**2)


class Person:
    def __init__(self, x, y, v, phi, om, state, teleportable, tp_spot=[0,0], tp_radius=0):
        self.x = x
        self.y = y
        self.vel = v
        self.angle = phi
        self.rot_vel = om
        self.state = state
        self.current_sick_time = 0
        self.sick_time = rnd.normal(300, 50)
        self.teleportable = teleportable
        self.tp_chance = 0.01
        self.tp_cooldown = 15
        self.tp_time = 0
        self.tp_back_cooldown = 15
        self.tp_spot = tp_spot
        self.tp_radius = tp_radius
        self.tpd = False
        self.last_pos = [self.x, self.y]
        self.matrix_pos = [0,0]
        self.death_risk = 0.00005

    def update(self, area):
        if self.state != 3:
            if self.teleportable:
                self.teleport()

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


    def draw(self, area, colors, distance):
        #Ritar cirklar i olika färger beroende på tillstånd
        pygame.draw.circle(screen, (150,150,150), (int(area.x + self.x), int(area.y + self.y)), int(distance/2), 1)
        pygame.draw.circle(screen, colors[self.state], (int(area.x + self.x), int(area.y + self.y)), 3)

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
    def __init__(self, n, area, standard_distance, standard_velocity, infected_ratio):
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
        self.population_matrix = PopulationMatrix(self.area, self.distance)
        self.vel = standard_velocity/n**(1/2)
        self.rot_vel = np.pi/15
        inf = math.ceil(max(1, n*infected_ratio))
        for i in range(n-inf):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 0)
        for i in range(inf):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 1)


    def add_person(self, x, y, sick):
        if self.area.market_on:
            p = Person(x, y, self.vel, 2 * np.pi * rnd.random(), self.rot_vel, sick, True, tp_spot=self.area.tp_spot, tp_radius=self.area.tp_radius)
        else:
            p = Person(x, y, self.vel, 2 * np.pi * rnd.random(), self.rot_vel, sick, False)
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
    def __init__(self, x, y, w, h, tp_spot, radius, n, market_on):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.tp_spot = tp_spot
        self.tp_radius = radius
        self.market_text = font2.render("SUPERMARKET", True, (255,0,0))
        self.market_on = market_on

    def draw(self):
        pygame.draw.rect(screen, (240,240,230), (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)
        if self.market_on:
            pygame.draw.circle(screen, (255,200,200), (self.x+self.tp_spot[0], self.y+self.tp_spot[1]), self.tp_radius)
            pygame.draw.circle(screen, (255,0,0), (self.x+self.tp_spot[0], self.y+self.tp_spot[1]), self.tp_radius, 1)
            screen.blit(self.market_text, (self.x+self.tp_spot[0]-self.market_text.get_width()/2, self.y+self.tp_spot[1]-self.market_text.get_height()/2))


class Manager:
    def __init__(self, population):
        self.population = population
        self.inf_prob = 0.01
        self.distance = self.population.distance
        self.colors = [(0,0,0),(255,0,0),(0,0,255),(100,100,100),(127,0,255)]

    def update(self, population, graphics):
        #Skriv ut text
        if graphics:
            pop_text = font1.render(("Population: "+str(population.size)), True, (0,0,0))
            screen.blit(pop_text, (25,25))
            states = ["Susceptible", "Infected", "Recovered", "Dead"]
            for i in range(len(states)):
                text = font1.render((states[i]+": "+str(population.distribution[states[i]])), True, self.colors[i])
                screen.blit(text, (25, 25+25*(i+1)))

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
            if graphics:
                person.draw(population.area, self.colors, population.population_matrix.safe_distance)

    def infect(self, person):
        self.population.distribution["Susceptible"] -= 1
        self.population.distribution["Infected"] += 1
        person.state = 1


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
    global graphics
    graphics = True
    n = 100
    std_distance = 350
    std_velocity = 14
    market_on = False
    area = Area(25, 165, 600, 400, [200,200], 50, n, market_on)
    population = Population(n, area, std_distance, std_velocity, 0.001)
    manager = Manager(population)
    stats = Stats(population, manager.colors)
    #Huvudloop där allt uppdateras
    if graphics:
        while True:
            screen.fill((255, 255, 255))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    quit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    x, y = pygame.mouse.get_pos()
                    if area.width > x-area.x > 0 and area.height > y-area.y > 0:
                        if event.button == 1:
                            population.add_person(x-area.x, y-area.y, False)
                        if event.button == 3:
                            population.add_person(x-area.x, y-area.y, True)
            area.draw()
            manager.update(population, graphics)
            stats.update()
            pygame.display.update()
            clock.tick(fps)
    else:
        frames = 0
        while True:
            manager.update(population, graphics)
            done = stats.update()
            if done:
                pygame.quit()
                break
            frames += 1
            if frames % 15 == 0:
                print(frames)
                print(stats.current_stats())

main()
