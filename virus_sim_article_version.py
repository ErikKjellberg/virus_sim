import pygame
import math
import numpy as np
import numpy.random as rnd
import matplotlib.pyplot as plt
import time

pygame.init()
font1 = pygame.font.SysFont("courier", 24)
font2 = pygame.font.SysFont("Arial", 12, italic=True, bold=True)
width, height = 1000, 700
screen = pygame.display.set_mode((width, height))
clock = pygame.time.Clock()
fps = 15

SUSCEPTIBLE = 0
INFECTED = 1
RECOVERED = 2
DEAD = 3
VACCINATED = 4

def distance(x1, x2, y1, y2):
    return np.sqrt((y2-y1)**2+(x2-x1)**2)


class Person:
    def __init__(self, x, y, v, phi, om, state, teleportable, tp_spot, tp_radius):
        self.x = x
        self.y = y
        self.vel = v
        self.angle = phi
        self.rot_vel = om
        self.state = state
        self.current_sick_time = 0
        self.recover_time = rnd.normal(300, 50)
        self.teleportable = teleportable
        self.tp_chance = 0.01
        self.tp_cooldown = 15
        self.tp_time = 0
        self.tp_back_cooldown = 15
        self.tp_spot = tp_spot
        self.tp_radius = tp_radius
        self.teleported = False
        self.last_pos = [self.x, self.y]
        self.mat_pos = [0,0]
        self.death_risk = 0.00005
        self.vaccination_rate = 0.001
        self.r_val = 0

    def update(self, area):
        if self.state != DEAD:
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
            if self.state == INFECTED:
                self.current_sick_time += 1
                #Död
                if rnd.random() < self.death_risk:
                    return DEAD
                #Tillfriskning
                if self.current_sick_time >= self.recover_time:
                    return RECOVERED
            #Chans till vaccin
            elif self.state == SUSCEPTIBLE:
                if rnd.random() < self.vaccination_rate:
                    return VACCINATED
        # Om inget intressant hände
        return 0

    def teleport(self):
        if not self.teleported:
            if rnd.random() < self.tp_chance and self.tp_time >= self.tp_cooldown:
                self.last_pos = [self.x, self.y]
                r = rnd.rand()*self.tp_radius
                theta = rnd.random()*2*np.pi
                tp_x = self.tp_spot[0] + r * np.cos(theta)
                tp_y = self.tp_spot[1] + r * np.sin(theta)
                self.x = tp_x
                self.y = tp_y
                self.tp_time = 0
                self.teleported = True
            else:
                self.tp_time += 1
        else:
            if self.tp_time >= self.tp_back_cooldown:
                self.x = self.last_pos[0]
                self.y = self.last_pos[1]
                self.teleported = False
                self.tp_time = 0
            else:
                self.tp_time += 1

    def draw(self, area, colors, distance):
        #Ritar cirklar i olika färger beroende på tillstånd
        pygame.draw.circle(screen, (150,150,150), (int(area.x + self.x), int(area.y + self.y)), int(distance/2), 1)
        pygame.draw.circle(screen, colors[self.state], (int(area.x + self.x), int(area.y + self.y)), 3)


class PopulationMatrix:  # Skapar matris för avståndsbedömning
    def __init__(self, area, safe_distance):
        self.mat_pop = []
        self.safe_distance = safe_distance
        self.width = math.ceil(area.width//safe_distance)
        self.height = math.ceil(area.height//safe_distance)
        for i in range(self.width):
            self.mat_pop.append([])
            for j in range(self.height):
                self.mat_pop[i].append([])

    def add_pop(self, pop_list):  # Lägger in pop i matrisen
        for person in pop_list:
            self.add_person(person)

    def add_person(self,person):  # Lägger till en person i matrisen
        person.mat_pos = self.fix_mat_pos([math.floor(person.x//self.safe_distance), math.floor(person.y//self.safe_distance)])
        self.mat_pop[person.mat_pos[0]][person.mat_pos[1]].append(person)

    def update_person(self, person):  # Uppdaterar personens matrix pos efter att positionen har ändrats
        matrix_pos = self.fix_mat_pos(person.mat_pos)

        person.mat_pos = [math.floor(person.x//self.safe_distance), math.floor(person.y//self.safe_distance)]
        self.mat_pop[matrix_pos[0]][matrix_pos[1]].remove(person)
        if person.state == INFECTED:
            self.add_person(person)
            return False
        # Om personen har tillfrisknat läggs denne inte tillbaka i matrisen igen
        else:
            return True

    def fix_mat_pos(self, mat_pos):  # Rättar till en matrisposition om den har hamnat utanför matrisen
        if mat_pos[0] > self.width-1:
            mat_pos[0] = self.width-1
        if mat_pos[1] > self.height-1:
            mat_pos[1] = self.height-1
        return mat_pos

    def check_distance(self,pop):  # Returnernar ett set med par med individer som är för nära varandra
        t0 = time.time()
        too_close = set()
        for person in pop:
            matrix_pos = self.fix_mat_pos([math.floor(person.x//self.safe_distance), math.floor(person.y//self.safe_distance)])
            # Tittar efter infekterade individer i de (vanligtvis) 8 omkringliggande rutorna
            for i in range(matrix_pos[0] - 1, min(self.width, matrix_pos[0] + 2)):
                for j in range(matrix_pos[1] - 1, min(self.height, matrix_pos[1] + 2)):
                    for person_2 in self.mat_pop[i][j]:
                        if distance(person.x, person_2.x, person.y, person_2.y) < self.safe_distance:
                            too_close.add((person, person_2))
        #print(time.time()-t0)
        return too_close


class Population:
    def __init__(self, n, area, standard_distance, standard_velocity, infected_ratio):
        self.size = 0
        # En dictionary som endast håller ordning på antalet i varje kategori
        self.distribution = {}
        self.distribution["Susceptible"] = 0
        self.distribution["Infected"] = 0
        self.distribution["Recovered"] = 0
        self.distribution["Dead"] = 0
        self.distribution["Vaccinated"] = 0

        # En mängd med hela populationen och tre mängder med S-, I- och R-delarna av populationen
        self.population_list = set()
        self.susceptible_population = set()
        self.infected_population = set()
        self.removed_population = set()
        self.area = area
        self.teleportable = (self.area.tp_spot != None)
        # Avståndet för möjlighet till smittspridning är inversproportinellt mot roten ur populationsstorleken,
        self.distance = standard_distance/n**(1/2)
        self.r_values = []
        self.population_matrix = PopulationMatrix(self.area, self.distance)
        self.vel = standard_velocity/n**(1/2)
        self.rot_vel = np.pi/15
        inf = math.ceil(max(1, n*infected_ratio))
        for i in range(n-inf):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 0)
        for i in range(inf):
            self.add_person(rnd.randint(0, self.area.width), rnd.randint(0, self.area.height), 1)


    def add_person(self, x, y, infected):
        p = Person(x, y, self.vel, 2 * np.pi * rnd.random(), self.rot_vel, infected, self.teleportable, self.area.tp_spot, self.area.tp_radius)
        self.population_list.add(p)
        if infected:
            self.population_matrix.add_person(p)
        self.size += 1
        if infected:
            self.infected_population.add(p)
            self.distribution["Infected"] += 1
        else:
            self.susceptible_population.add(p)
            self.distribution["Susceptible"] += 1

    def move_to_infected(self, person):
        if person in self.susceptible_population:
            self.susceptible_population.remove(person)
        self.infected_population.add(person)

    def move_to_removed(self, person):
        if person in self.infected_population:
            self.infected_population.remove(person)
        if person in self.susceptible_population:
            self.susceptible_population.remove(person)
        self.removed_population.add(person)


    def size(self):
        return len(self.susceptible_population)+len(self.infected_population)+len(self.removed_population)


class Area:
    def __init__(self, x, y, w, h, n, tp_spot=None, tp_radius=None):
        self.x = x
        self.y = y
        self.width = w
        self.height = h
        self.tp_spot = tp_spot
        self.tp_radius = tp_radius
        self.market_text = font2.render("SUPERMARKET", True, (255,0,0))

    def draw(self):
        pygame.draw.rect(screen, (240,240,230), (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, (0, 0, 0), (self.x, self.y, self.width, self.height), 2)
        if self.tp_spot != None:
            pygame.draw.circle(screen, (255,200,200), (self.x+self.tp_spot[0], self.y+self.tp_spot[1]), self.tp_radius)
            pygame.draw.circle(screen, (255,0,0), (self.x+self.tp_spot[0], self.y+self.tp_spot[1]), self.tp_radius, 1)
            screen.blit(self.market_text, (self.x+self.tp_spot[0]-self.market_text.get_width()/2, self.y+self.tp_spot[1]-self.market_text.get_height()/2))


class Manager:
    def __init__(self, population, vaccination_rate=0):
        if vaccination_rate != 0:
            self.vaccination_rate = vaccination_rate
        else:
            self.vaccination_rate = 0
        self.population = population
        self.inf_prob = 0.005
        self.distance = self.population.distance
        # Färger för de olika tillstånden
        self.colors = [(0,0,0),(255,0,0),(0,0,255),(100,100,100),(127,0,255)]
        self.frame = 0
        self.latest_r0 = "0"

    def update(self, population, graphics):
        self.frame += 1
        #Skriv ut text
        if self.vaccination_rate != 0:
            self.constant_vaccination()

        if graphics:
            pop_text = font1.render(("Population: "+str(population.size)), True, (0,0,0))
            screen.blit(pop_text, (0,0))
            states = ["Susceptible", "Infected", "Recovered", "Dead", "Vaccinated"]
            for i in range(len(states)):
                text = font1.render((states[i]+": "+str(population.distribution[states[i]])), True, self.colors[i])
                screen.blit(text, (0, 25*(i+1)))
            immunity_text = font1.render(("Immunity "+str(int(100*round((population.distribution["Recovered"]+population.distribution["Vaccinated"])/(population.size-population.distribution["Dead"]),2)))+"%"), True, (26,109,192))
            screen.blit(immunity_text, (0,25*6))
            sum = 0
            to_remove = []
            for i in population.r_values:
                sum+=i[0]
                i[1]+=1
                if i[1]==50:
                    to_remove.append(population.r_values.index(i))

            if len(population.r_values)!=0:
                self.latest_r0 = str(round(sum/len(population.r_values),2))
            for i in to_remove:
                population.r_values.remove(i)

            r0_text = font1.render(("R_0: "+self.latest_r0), True, (62,144,84))
            screen.blit(r0_text, (0,25*7))

        #Undersöker om smittspridning kan ske

        close_persons = population.population_matrix.check_distance(population.susceptible_population)
        recently_infected = set()
        for pair in close_persons:
            if not pair[0] in recently_infected:
                if rnd.random()<self.inf_prob:
                    recently_infected.add(pair[0])
                    self.infect(pair[0])
                    pair[1].r_val+=1
        population.r_values = []
        recently_recovered = set()
        recently_dead = set()
        for person in population.population_list:
            #Kör update för varje person
            update_state = person.update(population.area)
            # De som precis tillfrisknat
            if update_state == RECOVERED:
                self.recover(person)
                recently_recovered.add(person)
                #Lägger till varje nyligen recovered persons r_val i listan
                population.r_values.append([person.r_val,0])
            # De som precis dött
            elif update_state == DEAD:
                self.kill(person)
                recently_dead.add(person)
            # De som precis vaccinerats
            elif update_state == VACCINATED:
                self.vaccinate(person)
            if graphics:
                person.draw(population.area, self.colors, population.population_matrix.safe_distance)

        # Uppdaterar alla infekterade och nyligen tillfrisknade individers matrisposition
        for p in self.population.infected_population | recently_recovered | recently_dead:
            self.population.population_matrix.update_person(p)

    def infect(self, person):
        self.population.distribution["Susceptible"] -= 1
        self.population.distribution["Infected"] += 1
        self.population.population_matrix.add_person(person)
        self.population.move_to_infected(person)
        person.state = INFECTED

    def recover(self, person):
        self.population.distribution["Infected"] -= 1
        self.population.distribution["Recovered"] += 1
        self.population.move_to_removed(person)
        person.state = RECOVERED

    def kill(self, person):
        self.population.distribution["Infected"] -= 1
        self.population.distribution["Dead"] += 1
        self.population.move_to_removed(person)
        person.state = DEAD

    def vaccinate(self, person):
        self.population.distribution["Susceptible"] -= 1
        self.population.distribution["Vaccinated"] += 1
        self.population.move_to_removed(person)
        person.state = VACCINATED

    def constant_vaccination(self):
        vaccinated_this_frame = 0
        if self.vaccination_rate >= 1:
            # vaccinera self.vaccination_rate personer
            vaccinated_this_frame = int(self.vaccination_rate)
        else:
            frames = int(1/self.vaccination_rate)
            if self.frame % frames == 0:
                vaccinated_this_frame = 1
            else:
                vaccinated_this_frame = 0
        susceptible = len(self.population.susceptible_population)
        if susceptible > 0:
            for i in range(vaccinated_this_frame):
                list_temp = list(self.population.susceptible_population)
                p = rnd.choice(list_temp)
                self.vaccinate(p)


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
    n = 2000
    # Konstanter för standardavståndet för smittspridning och standardhastigheten för individerna
    std_distance = 350
    std_velocity = 14
    teleporting_allowed = False
    # Skapar området, populationen, en manager som tar hand om smittans utveckling, samt ett statistiskinsamlarobjekt
    if teleporting_allowed:
        teleport_spot = [200,200]
        teleport_radius = 50
        area = Area(100, 215, 600, 400, n, tp_spot=teleport_spot, tp_radius=teleport_radius)
    else:
        area = Area(100, 215, 600, 400, n)
    population = Population(n, area, std_distance, std_velocity, 0.005)
    manager = Manager(population, vaccination_rate=0)
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
                    # Användaren kan lägga till egna individer
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
            if frames % 150 == 0:
                print(frames)
                print(stats.current_stats())

main()
