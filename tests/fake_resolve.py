"""In-memory stand-ins for the Resolve scripting objects the workflow uses."""

from colormatch.imageio import save_png

FRAME_RATE = 24
TIMELINE_START = 86400


def timecode_to_frame(timecode):
    hours, minutes, seconds, frames = (int(part) for part in timecode.replace(";", ":").split(":"))

    return ((hours * 60 + minutes) * 60 + seconds) * FRAME_RATE + frames


class FakeGraph:
    def __init__(self, events, node_count=3, accepts_lut=True):
        self.events = events
        self.node_count = node_count
        self.accepts_lut = accepts_lut
        self.luts = {}
        self.enabled_calls = []

    def GetNumNodes(self):
        return self.node_count

    def SetLUT(self, node, path):
        self.events.append("SetLUT")

        if not self.accepts_lut:
            return False

        self.luts[node] = path

        return True

    def SetNodeEnabled(self, node, enabled):
        self.enabled_calls.append((node, enabled))

        return True


class FakeItem:
    def __init__(self, unique_id, name, start, duration, image, graph, colour=""):
        self.unique_id = unique_id
        self.name = name
        self.start = start
        self.duration = duration
        self.image = image
        self.graph = graph
        self.colour = colour

    def GetUniqueId(self):
        return self.unique_id

    def GetName(self):
        return self.name

    def GetStart(self):
        return self.start

    def GetDuration(self):
        return self.duration

    def GetClipColor(self):
        return self.colour

    def GetNodeGraph(self):
        return self.graph

    def contains(self, frame):
        return self.start <= frame < self.start + self.duration


class LegacyItem(FakeItem):
    """A Resolve 18 timeline item: node methods live on the item itself."""

    def GetNodeGraph(self):
        raise AttributeError("GetNodeGraph")

    def GetNumNodes(self):
        return self.graph.GetNumNodes()

    def SetLUT(self, node, path):
        return self.graph.SetLUT(node, path)


class FakeTimeline:
    def __init__(self, items, playhead):
        self.items = items
        self.timecode = playhead
        self.visited = []

    def GetName(self):
        return "Escena 1"

    def GetSetting(self, name):
        return {"timelineFrameRate": str(FRAME_RATE), "timelineDropFrameTimecode": "0"}[name]

    def GetCurrentTimecode(self):
        return self.timecode

    def SetCurrentTimecode(self, timecode):
        self.timecode = timecode
        self.visited.append(timecode)

        return True

    def GetCurrentVideoItem(self):
        frame = timecode_to_frame(self.timecode)

        return next((item for item in self.items if item.contains(frame)), None)

    def GetItemListInTrack(self, track_type, index):
        return list(self.items) if (track_type, index) == ("video", 1) else []


class FakeProject:
    def __init__(self, timeline, events, failing_items=()):
        self.timeline = timeline
        self.events = events
        self.failing_items = set(failing_items)

    def GetCurrentTimeline(self):
        return self.timeline

    def ExportCurrentFrameAsStill(self, path):
        item = self.timeline.GetCurrentVideoItem()

        if item is None or item.unique_id in self.failing_items:
            return False

        save_png(path, item.image)

        return True

    def RefreshLUTList(self):
        self.events.append("RefreshLUTList")

        return True


class FakeProjectManager:
    def __init__(self, project):
        self.project = project

    def GetCurrentProject(self):
        return self.project


class FakeResolve:
    def __init__(self, project):
        self.manager = FakeProjectManager(project)
        self.pages = []

    def GetProjectManager(self):
        return self.manager

    def OpenPage(self, name):
        self.pages.append(name)

        return True
