import pygame
import numpy as np
import numpy.random as rnd
import matplotlib.pyplot as plt

pygame.init()
width, height = 1000, 600
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
fps = 15

font1 = pygame.font.SysFont("courier", 24)


def distance(x1, x2, y1, y2):
    return np.sqrt((y2-y1)**2+(x2-x1)**2)


class Person:
    def __init__(self, x, y, v, phi, om, state, tp_spot, tp_radius):
        self.x = x
        self.y = y
        self.vel = v
        self.angle = phi
        self.rot_vel = om
        self.state = state
        self.current_sick_time = 0
        self.sick_time = 300
        self.tp_chance = 0.01
        self.tp_cooldown = 15
        self.tp_time = 0
        self.tp_back_cooldown = 15
        self.tp_spot = tp_spot
        self.tp_radius = tp_radius
        self.tpd = False
        self.last_pos = [self.x, self.y]
        self.death_risk = 0.001

    def update(self, area):
        if self.state != 3:
            self.teleport()

            #Stega framåt
            self.x += self.vel * np.cos(self.angle)
            self.y += self.vel * np.sin(self.angle)

            #Se till att individerna inte får gå utanför boxen
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
            if self.current_sick_time == self.sick_time and self.state != 2:
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


    def draw(self, area, colors):
        #Ritar cirklar i olika färger beroende på tillstånd
        pygame.draw.circle(screen, colors[self.state], (int(area.x + self.x), int(area.y + self.y)), 3)


class Population:
    def __init__(self, n, area):
        self.size = 0
        self.distribution = {}
        self.distribution["Susceptible"] = 0
        self.distribution["Infected"] = 0
        self.distribution["Recovered"] = 0
        self.distribution["Dead"] = 0
        self.distribution["Vaccinated"] = 0
        self.population_list = []
        self.area = area
        self.vel = 2
        self.rot_vel = self.vel*np.pi/15
        for i in range(int(9*n/10)):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 0)
        for i in range(n-int(9*n/10)):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 1)

    def add_person(self, x, y, sick):
        self.population_list.append(Person(x, y, self.vel, 2 * np.pi * rnd.random(), self.rot_vel, sick, self.area.tp_spot, self.area.tp_radius))
        self.size += 1
        if sick:
            self.distribution["Infected"] += 1
        else:
            self.distribution["Susceptible"] += 1


    def size(self):
        return len(self.population_list)


class Area:
    def __init__(self, x, y, w, h, tp_spot, tp_radius):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.tp_spot = tp_spot
        self.tp_radius = tp_radius

    def draw(self):
        pygame.draw.rect(screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)
        pygame.draw.circle(screen, (255,100,100), (self.x+self.tp_spot[0], self.y+self.tp_spot[1]), self.tp_radius)


class Manager:
    def __init__(self, population):
        self.population = population
        self.inf_prob = 0.01
        self.distance = 50
        self.colors = [(0,0,0),(255,0,0),(0,0,255),(100,100,100)]

    def update(self, population):
        #Skriv ut text
        pop_text = font1.render(("Population: "+str(population.size)), True, (0,0,0))
        screen.blit(pop_text, (0,0))
        states = ["Susceptible", "Infected", "Recovered", "Dead"]
        for i in range(len(states)):
            text = font1.render((states[i]+": "+str(population.distribution[states[i]])), True, self.colors[i])
            screen.blit(text, (0, 25*(i+1)))

        #Undersöker om smittspridning kan ske
        for person in population.population_list:
            for person2 in population.population_list:
                if distance(person.x, person2.x, person.y, person2.y) <= self.distance and person.state == 1 and person2.state == 0:
                    if rnd.random()<self.inf_prob:
                        self.infect(person2)

            #Kör update för varje person
            state = person.update(population.area)
            if state == 1:
                population.distribution["Infected"] -= 1
                population.distribution["Recovered"] += 1
            elif state == -1:
                population.distribution["Infected"] -= 1
                population.distribution["Dead"] += 1
            person.draw(population.area, self.colors)

    def infect(self, person):
        self.population.distribution["Susceptible"] -= 1
        self.population.distribution["Infected"] += 1
        person.state = 1


def main():
    area = Area(100, 150, 600, 400, [200,200], 50)
    population = Population(50, area)
    manager = Manager(population)

    #Huvudloop där allt uppdateras
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
        manager.update(population)
        pygame.display.update()
        clock.tick(fps)


main()
