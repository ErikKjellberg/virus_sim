import math
import random
import pickle


width, height = 1000, 700

SUSCEPTIBLE = 0
INFECTED = 1
RECOVERED = 2
DEAD = 3
VACCINATED = 4

def distance(x1, x2, y1, y2):
    return math.sqrt((y2-y1)**2+(x2-x1)**2)


class Person:
    def __init__(self, x, y, v, phi, om, state, teleportable, tp_spot, tp_radius):
        global death_risk
        global vaccination_raten
        self.x = x
        self.y = y
        self.vel = v
        self.angle = phi
        self.rot_vel = om
        self.state = state
        self.current_sick_time = 0
        self.recover_time = random.normalvariate(300, 50)
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
        self.death_risk = death_risk
        self.vaccination_rate = vaccination_raten
        self.r_val = 0

    def update(self, area):
        if self.state != DEAD:
            if self.teleportable:
                self.teleport()

            #Stega framåt
            self.x += self.vel * math.cos(self.angle)
            self.y += self.vel * math.sin(self.angle)

            #Se till att individerna inte får gå utanför området
            if not area.width > self.x > 0 or not area.height > self.y > 0:
                self.angle += math.pi
                if self.x < 0:
                    self.x = 0
                if self.x > area.width:
                    self.x = area.width
                if self.y < 0:
                    self.y = 0
                if self.y > area.height:
                    self.y = area.height

            #Rotera slumpmässigt
            if random.random() >= 0.5:
                self.angle += random.random()*self.rot_vel
            else:
                self.angle -= random.random()*self.rot_vel

            #Vad händer när man är infekterad?
            if self.state == INFECTED:
                self.current_sick_time += 1
                #Död
                if random.random() < self.death_risk:
                    return DEAD
                #Tillfriskning
                if self.current_sick_time >= self.recover_time:
                    return RECOVERED
            #Chans till vaccin
            elif self.state == SUSCEPTIBLE:
                if random.random() < self.vaccination_rate:
                    return VACCINATED
        # Om inget intressant hände
        return 0

    def teleport(self):
        if not self.teleported:
            if random.random() < self.tp_chance and self.tp_time >= self.tp_cooldown:
                self.last_pos = [self.x, self.y]
                r = random.random()*self.tp_radius
                theta = random.random()*2*math.pi
                tp_x = self.tp_spot[0] + r * math.cos(theta)
                tp_y = self.tp_spot[1] + r * math.sin(theta)
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


class PopulationMatrix:  # Skapar matris för avståndsbedömning
    def __init__(self, area, safe_distance):
        self.mat_pop = []
        self.safe_distance = safe_distance
        self.width = int(area.width//safe_distance)
        self.height = int(area.height//safe_distance)
        for i in range(self.width):
            self.mat_pop.append([])
            for j in range(self.height):
                self.mat_pop[i].append(set())

    def add_pop(self, pop_list):  # Lägger in pop i matrisen
        for person in pop_list:
            self.add_person(person)

    def add_person(self,person):  # Lägger till en person i matrisen
        person.mat_pos = self.fix_mat_pos([int(person.x//self.safe_distance), int(person.y//self.safe_distance)])
        self.mat_pop[person.mat_pos[0]][person.mat_pos[1]].add(person)

    def update_person(self, person):  # Uppdaterar personens matrix pos efter att positionen har ändrats
        matrix_pos = self.fix_mat_pos(person.mat_pos)
        person.mat_pos = [int(person.x//self.safe_distance), int(person.y//self.safe_distance)]
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
        too_close = set()
        for person in pop:
            matrix_pos = self.fix_mat_pos([int(person.x//self.safe_distance), int(person.y//self.safe_distance)])
            # Tittar efter infekterade individer i de (vanligtvis) 8 omkringliggande rutorna
            for i in range(matrix_pos[0] - 1, min(self.width, matrix_pos[0] + 2)):
                for j in range(matrix_pos[1] - 1, min(self.height, matrix_pos[1] + 2)):
                    for person_2 in self.mat_pop[i][j]:
                        if distance(person.x, person_2.x, person.y, person_2.y) < self.safe_distance:
                            too_close.add((person, person_2))
        return too_close


class Population:
    def __init__(self, n, area, standard_distance, standard_velocity, infected):
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

        self.distance = standard_distance/pow(n,1/2)
        self.r_values = []
        self.population_matrix = PopulationMatrix(self.area, self.distance)
        self.vel = standard_velocity/pow(n,1/2)
        self.rot_vel = math.pi/15
        inf = infected
        for i in range(inf,n):
            self.add_person(random.random()*self.area.width, random.random()*self.area.height, 0)
        for i in range(inf):
            self.add_person(random.random()*self.area.width, random.random()*self.area.height, 1)


    def add_person(self, x, y, infected):
        p = Person(x, y, self.vel, 2 * math.pi * random.random(), self.rot_vel, infected, self.teleportable, self.area.tp_spot, self.area.tp_radius)
        self.population_list.add(p)
        self.size += 1
        if infected:
            self.population_matrix.add_person(p)
            self.infected_population.add(p)
            self.distribution["Infected"] += 1
        else:
            self.susceptible_population.add(p)
            self.distribution["Susceptible"] += 1

    def move_to_infected(self, person):
        self.susceptible_population.remove(person)
        self.infected_population.add(person)

    def move_to_removed(self, person):
        if person in self.infected_population:
            self.infected_population.remove(person)
        else:
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

class Manager:
    def __init__(self, population, vaccination_rate, inf_prob):
        self.vaccination_rate = vaccination_rate
        self.population = population
        self.inf_prob = inf_prob
        self.distance = self.population.distance
        # Färger för de olika tillstånden
        self.frame = 0

    def update(self, population):
        self.frame += 1
        #Skriv ut text
        if self.vaccination_rate != 0:
            self.constant_vaccination()
        #Undersöker om smittspridning kan ske
        close_persons = population.population_matrix.check_distance(population.susceptible_population)
        recently_infected = set()
        recently_recovered = set()
        recently_dead = set()

        for pair in close_persons:
            if not pair[0] in recently_infected:
                if random.random()<self.inf_prob:
                    recently_infected.add(pair[0])
                    self.infect(pair[0])

        for person in population.population_list:
            #Kör update för varje person
            update_state = person.update(population.area)
            # De som precis tillfrisknat
            if update_state == RECOVERED:
                self.recover(person)
                recently_recovered.add(person)
            # De som precis dött
            elif update_state == DEAD:
                self.kill(person)
                recently_dead.add(person)
            # De som precis vaccinerats
            elif update_state == VACCINATED:
                self.vaccinate(person)

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
                p = random.choice(list_temp)
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
        if self.data["Infected"][-1] <= 50 and self.done == False:
            self.done = True
            with open('Data_save.pkl', 'wb') as f:
                pickle.dump(self.data,f)
        return self.done

    def current_stats(self):
        s = ""
        for key in self.data.keys():
            s += key + ": " + str(self.data[key][-1]) + "\n"
        return s


def main():
    n = 20000
    # Konstanter för standardavståndet för smittspridning och standardhastigheten för individerna
    global death_risk
    global vaccination_raten
    std_distance = 350
    std_velocity = 14
    teleporting_allowed = True
    vaccination_rate = 0
    colors = [(0,0,0),(255,0,0),(0,0,255),(100,100,100),(127,0,255)]
    amount_infected = 100
    inf_prob= 0.005
    death_risk = 0.00005
    vaccination_raten = 0
       # Skapar området, populationen, en manager som tar hand om smittans utveckling, samt ett statistiskinsamlarobjekt
    if teleporting_allowed:
        teleport_spot = [200,200]
        teleport_radius = 50
        area = Area(100, 215, 600, 400, n, tp_spot=teleport_spot, tp_radius=teleport_radius)
    else:
        area = Area(100, 215, 600, 400, n)
    population = Population(n, area, std_distance, std_velocity, amount_infected)
    manager = Manager(population, vaccination_rate, inf_prob)
    stats = Stats(population, colors)
    #Huvudloop där allt uppdateras
    frames = 0
    while True:
        manager.update(population)
        done = stats.update()
        if done:
            break
        frames += 1
main()
