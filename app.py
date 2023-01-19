
"""
App'en er skabt i formålet om at hjælpe patienter med deres morgenrutine
efter en knæoperation
"""
import toga
import xmltodict as xmltodict
from toga.style import Pack
from toga.style.pack import COLUMN, ROW
from services import database_connection as dbc

import httpx
import xml.etree.ElementTree as ET


class Daily(toga.App):

    def startup(self):
        self.graph_id = 1329742
        self.simulationwindow = 0
        self.simulationid = None

        login_box = toga.Box(style=Pack(direction=COLUMN))
        login = toga.Button(
            'Login',
            on_press=self.show_login_window,
            style=Pack(padding=5)
        )
        login_box.add(login)

        self.main_window = toga.MainWindow(title=self.formal_name)
        self.main_window.content = login_box
        self.main_window.show()

    def show_login_window(self, widget):
        self.second_window = toga.Window(title='Login')
        self.windows.add(self.second_window)
        login_box = toga.Box(style=Pack(direction=COLUMN))

        username_box = toga.Box(style=Pack(direction=ROW, padding=5))
        user_label = toga.Label(
            'Username: ',
            style=Pack(padding=(0, 10))
        )
        self.user_input = toga.TextInput(style=Pack(flex=1), placeholder='enter your DCR email', value='sdw790@alumni.ku.dk')
        username_box.add(user_label)
        username_box.add(self.user_input)

        password_box = toga.Box(style=Pack(direction=ROW, padding=5))
        passwd_label = toga.Label(
            'Password: ',
            style=Pack(padding=(0, 10))
        )
        self.password_input = toga.PasswordInput(style=Pack(flex=1), value='Dchu4klm')
        password_box.add(passwd_label)
        password_box.add(self.password_input)

        login_button = toga.Button(
            'Login',
            on_press=self.login,
            style=Pack(padding=5)
        )

        login_box.add(username_box)
        login_box.add(password_box)
        login_box.add(login_button)

        self.second_window.content = login_box
        self.second_window.show()

    async def create_instance(self, widget):

        async with httpx.AsyncClient() as client:
            response = await client.post("https://repository.dcrgraphs.net/api/graphs/" + str(self.graph_id) + "/sims",
                                         auth=(self.user_input, self.password_input.value))

        self.simulationid = response.headers['simulationid']
        print("New simulation created with id:", self.simulationid)

    async def login(self, widget):
        async with httpx.AsyncClient() as client:
            response = await client.get(f"https://repository.dcrgraphs.net/api/graphs/{self.graph_id}/sims",
                                        auth=(self.user_input.value, self.password_input.value))
        print(response.text)
        root = ET.fromstring(response.text)
        self.sims = {}
        self.username = self.user_input.value
        self.password = self.password_input.value
        dbc.db_connect()
        role = dbc.execute_query(self.username)
        print(role)

        for s in root.findall("trace"):
            print(f"[i] id: {s.attrib['id']}, title: {s.attrib['title']}")
            self.sims[s.attrib['id']] = "Instance:"+s.attrib['id']
        self.second_window.close()
        self.show_sim_list()

    def show_sim_list(self):
        container = toga.ScrollContainer(horizontal=False, )
        sims_box = toga.Box(style=Pack(direction=COLUMN))
        container.content = sims_box
        for id, name in self.sims.items():
            g_button = toga.Button(
                name,
                on_press=self.show_enabledactivities,
                style=Pack(padding=5),
                id=id
            )
            sims_box.add(g_button)
        g_button = toga.Button(
            "Create new instance",
            on_press=self.create_show_enabled_activities,
            style=Pack(padding=5)
        )

        button2 = toga.Button(
            'Delete entered instance',
            on_press=self.delete_instance,
            style=Pack(padding=5)
        )
        self.delete_input = toga.TextInput(style=Pack(padding=5),placeholder='Enter DCR ID')

        sims_box.add(button2)
        sims_box.add(g_button)
        self.main_window.content = container

    async def show_enabledactivities(self, widget):
        async with httpx.AsyncClient() as client:
            enabledevents = await client.get(
                "https://repository.dcrgraphs.net/api/graphs/" + str(self.graph_id) + "/sims/" + self.simulationid + "/events?filter=only-enabled",
                auth=(self.username.value, self.password.value))
        eventsxml = enabledevents.text
        eventsxmlnoquote = eventsxml[1:len(eventsxml) - 1]
        eventsxmlclean = eventsxmlnoquote.replace('\\\"', '\"')
        eventsjson = xmltodict.parse(eventsxmlclean)
        events = eventsjson['events']
        print("Enabled events")
        for e in events['event']:
            print(e['@label'])

    async def create_show_enabled_activities(self, widget):
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://repository.dcrgraphs.net/api/graphs/{self.graph_id}/sims",
                auth=(self.username, self.password))
            self.simulationid = response.headers['simulationid']

            enabled_events = await self.get_enabled_events()
        print(enabled_events.json())
        root = ET.fromstring(enabled_events.json())
        events = root.findall('event')
        self.show_activities_window(events)

    def show_activities_window(self, events):
        if self.simulationwindow != 0:
              self.activities_window.close()
        self.activities_window = toga.Window(title=f'Simulation #{self.simulationid}')
        self.simulationwindow=1
        self.windows.add(self.activities_window)

        self.update_activities_box(events)
        self.activities_window.show()

    async def execute_activity(self, widget):
        enabled_events = None
        event_id = widget.id
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://repository.dcrgraphs.net/api/graphs/{self.graph_id}/sims/{self.simulationid}/events/{event_id}",
                auth=(self.username, self.password))
        if len(response.text) == 0:
            enabled_events = await self.get_enabled_events()
        else:
            print(f'[!] {response.text}')
        if enabled_events:
            root = ET.fromstring(enabled_events.json())
            events = root.findall('event')
            self.update_activities_box(events)
        else:
            print("[!] No enabled events!")


    async def delete_instance(self,widget):
        self.sim_id = int(self.delete_input.value)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://repository.dcrgraphs.net/api/graphs/{self.graph_id}/sims/{self.simulationid}",
                auth=(self.username, self.password))
            print(response.status_code)
            await self.get_sims()
            self.show_sim_list()

    async def get_enabled_events(self):
        url = f"https://repository.dcrgraphs.net/api/graphs/{self.graph_id}/sims/{self.simulationid}/events?filter=only-enabled"
        async with httpx.AsyncClient() as client:
            return await client.get(url,  auth=(self.username, self.password))

    async def get_pending_events(self):
        url = f"https://repository.dcrgraphs.net/api/graphs/{self.graph_id}/sims/{self.simulationid}/events?filter=only-pending"
        async with httpx.AsyncClient() as client:
            return await client.get(url,  auth=(self.username, self.password))

    def update_activities_box(self, events):
        activities_box = toga.Box(style=Pack(direction=COLUMN))
        if len(events) >= 1:
            for e in events:
                e_button = toga.Button(
                    text=e.attrib['label'],
                    on_press=self.execute_activity,
                    style=Pack(padding=5),
                    id=e.attrib['id'],
                )
                activities_box.add(e_button)
        else:
            print("[!] No events to execute!")

        self.activities_window.content = activities_box

def main():
    return Daily()