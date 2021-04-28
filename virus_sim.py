import pygame
import numpy as np
import numpy.random as rnd
import matplotlib.pyplot as plt

pygame.init()
width, height = 1000, 600
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
fps = 60

font1 = pygame.font.SysFont("courier", 24)


def distance(x1, x2, y1, y2):
    return np.sqrt((y2-y1)**2+(x2-x1)**2)


class Person:
    def __init__(self, x, y, v, phi, om, sick):
        self.x = x
        self.y = y
        self.vel = v
        self.angle = phi
        self.rot_vel = om
        self.sick = sick

    def update(self, area):
        self.x += self.vel * np.cos(self.angle)
        self.y += self.vel * np.sin(self.angle)
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

        self.angle += rnd.choice([-1, 1])*rnd.random()*self.rot_vel

    def draw(self, area):
        if self.sick:
            pygame.draw.circle(screen, (255, 0, 0), (int(area.x + self.x), int(area.y + self.y)), 3)
            #pygame.draw.circle(screen, (0, 0, 0), (int(area.x + self.x), int(area.y + self.y)), 50, 1)
        else:
            pygame.draw.circle(screen, (0, 0, 0), (int(area.x + self.x), int(area.y + self.y)), 3)


class Population:
    def __init__(self, n, area):
        self.size = 0
        self.sicks = 0
        self.population_list = []
        self.area = area
        self.vel = 2
        self.rot_vel = self.vel*np.pi/15
        for i in range(int(9*n/10)):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), False)
        for i in range(n-int(9*n/10)):    
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), True)

    def add_person(self, x, y, sick):
        self.population_list.append(Person(x, y, self.vel, 2 * np.pi * rnd.random(), self.rot_vel, sick))
        self.size += 1
        if sick:
            self.sicks += 1

    def update(self):
        for person in self.population_list:
            for person2 in self.population_list:
                if distance(person.x, person2.x, person.y, person2.y) < 25:
                    pass
            person.update(self.area)
            person.draw(self.area)


class Area:
    def __init__(self, x, y, w, h):
        self.x = x
        self.y = y
        self.width = w
        self.height = h

    def draw(self):
        pygame.draw.rect(screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)


class GUI:
    def __init__(self, area):
        self.area = area

    def draw(self):
        pass


class Manager:
    def __init__(self, population):
        self.population = population
        self.inf_prob = 0.001
        self.distance = 50

    def update(self, population):
        pop_text = font1.render(("Population: "+str(population.size)), True, (0,0,0))
        sick_text = font1.render(("Infected: "+str(population.sicks)), True, (0,0,0))
        screen.blit(pop_text, (0,0))
        screen.blit(sick_text, (0,20))
        for person in population.population_list:
            for person2 in population.population_list:
                if distance(person.x, person2.x, person.y, person2.y) <= self.distance and person.sick and not person2.sick:
                    if rnd.random()<self.inf_prob:
                        self.infect(person2)
            person.update(population.area)
            person.draw(population.area)

    def infect(self, person):
        self.population.sicks += 1
        person.sick = True


def main():
    area = Area(100, 100, 600, 400)
    population = Population(50, area)
    manager = Manager(population)
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
        clock.tick(60)


main()
