import os
import tempfile
import unittest
from dataclasses import replace

from colormatch.colorspace import mean_delta_e
from colormatch.engine import PRESETS
from colormatch.imageio import save_png
from colormatch.lut import apply_lut, read_cube
from colormatch.workflow import WorkflowError, WorkflowOptions, lut_file_name, run
from tests import synthetic
from tests.fake_resolve import (
    TIMELINE_START,
    FakeGraph,
    FakeItem,
    FakeProject,
    FakeResolve,
    FakeTimeline,
    LegacyItem,
)

PLAYHEAD_ON_REFERENCE = "01:00:00:12"
CLIP_LENGTH = 48


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.events = []
        self.reference_image = synthetic.scene()
        self.warm_image = synthetic.graded(self.reference_image, white_balance=(1.3, 1.0, 0.7), exposure=0.7)
        self.cool_image = synthetic.graded(self.reference_image, white_balance=(0.8, 1.0, 1.3), exposure=1.3)
        self.graphs = [FakeGraph(self.events) for _ in range(3)]
        self.items = [
            FakeItem("ref", "Referencia", TIMELINE_START, CLIP_LENGTH, self.reference_image, self.graphs[0]),
            FakeItem("a", "Plano A", TIMELINE_START + CLIP_LENGTH, CLIP_LENGTH, self.warm_image, self.graphs[1], "Orange"),
            FakeItem("b", "Plano B", TIMELINE_START + 2 * CLIP_LENGTH, CLIP_LENGTH, self.cool_image, self.graphs[2]),
        ]
        self.timeline = FakeTimeline(self.items, PLAYHEAD_ON_REFERENCE)
        self.project = FakeProject(self.timeline, self.events)
        self.resolve = FakeResolve(self.project)
        self.options = WorkflowOptions(
            lut_folder=os.path.join(self.folder.name, "luts"),
            still_folder=os.path.join(self.folder.name, "stills"),
        )

    def tearDown(self):
        self.folder.cleanup()

    def test_given_a_reference_under_the_playhead_when_matching_then_every_other_clip_gets_a_matching_lut(self):
        # Act
        results = run(self.resolve, self.options)

        # Assert
        self.assertEqual([("Plano A", True), ("Plano B", True)], [(result.name, result.applied) for result in results])
        self.assertEqual({}, self.graphs[0].luts)
        for item, result in zip(self.items[1:], results):
            corrected = apply_lut(item.image, read_cube(result.lut_path))
            self.assertLess(mean_delta_e(corrected, self.reference_image), 0.3 * mean_delta_e(item.image, self.reference_image))

    def test_given_clips_with_several_nodes_when_matching_then_the_lut_goes_on_the_last_node(self):
        # Act
        results = run(self.resolve, self.options)

        # Assert
        self.assertEqual({3: results[0].lut_path}, self.graphs[1].luts)
        self.assertEqual({3: results[1].lut_path}, self.graphs[2].luts)

    def test_given_an_explicit_node_when_matching_then_the_lut_goes_on_that_node(self):
        # Arrange
        options = replace(self.options, node_index=2)

        # Act
        run(self.resolve, options)

        # Assert
        self.assertEqual([2], list(self.graphs[1].luts))

    def test_given_a_node_beyond_the_graph_when_matching_then_falls_back_to_the_last_node(self):
        # Arrange
        options = replace(self.options, node_index=9)

        # Act
        run(self.resolve, options)

        # Assert
        self.assertEqual([3], list(self.graphs[1].luts))

    def test_given_a_target_clip_when_grabbing_its_frame_then_the_match_node_is_bypassed_and_restored(self):
        # Act
        run(self.resolve, self.options)

        # Assert
        self.assertEqual([(3, False), (3, True)], self.graphs[1].enabled_calls)

    def test_given_new_luts_when_applying_them_then_resolve_refreshes_its_lut_list_first(self):
        # Act
        run(self.resolve, self.options)

        # Assert
        self.assertEqual(["RefreshLUTList", "SetLUT", "SetLUT"], self.events)

    def test_given_a_finished_run_when_checking_the_playhead_then_it_is_back_where_the_user_left_it(self):
        # Act
        run(self.resolve, self.options)

        # Assert
        self.assertEqual(PLAYHEAD_ON_REFERENCE, self.timeline.GetCurrentTimecode())
        self.assertEqual(["color"], self.resolve.pages)

    def test_given_a_target_clip_when_grabbing_then_the_playhead_visits_its_middle_frame(self):
        # Act
        run(self.resolve, self.options)

        # Assert
        self.assertEqual(["01:00:03:00", "01:00:05:00", PLAYHEAD_ON_REFERENCE], self.timeline.visited)

    def test_given_a_clip_colour_filter_when_matching_then_only_clips_of_that_colour_are_graded(self):
        # Arrange
        options = replace(self.options, clip_colour="orange")

        # Act
        results = run(self.resolve, options)

        # Assert
        self.assertEqual(["Plano A"], [result.name for result in results])
        self.assertEqual({}, self.graphs[2].luts)

    def test_given_an_external_reference_image_when_transferring_a_look_then_every_clip_is_graded(self):
        # Arrange
        look_path = os.path.join(self.folder.name, "look.png")
        save_png(look_path, synthetic.teal_orange(synthetic.scene(seed=8)))
        options = replace(self.options, mode="look", reference_image=look_path, settings=PRESETS["look"])

        # Act
        results = run(self.resolve, options)

        # Assert
        self.assertEqual(3, sum(1 for result in results if result.applied))

    def test_given_resolve_18_items_without_node_graphs_when_matching_then_the_lut_is_set_on_the_item(self):
        # Arrange
        legacy = LegacyItem("old", "Plano antiguo", TIMELINE_START + CLIP_LENGTH, CLIP_LENGTH, self.warm_image, self.graphs[1])
        self.timeline.items = [self.items[0], legacy]

        # Act
        results = run(self.resolve, self.options)

        # Assert
        self.assertTrue(results[0].applied)
        self.assertEqual({3: results[0].lut_path}, self.graphs[1].luts)

    def test_given_no_clip_under_the_playhead_when_matching_then_raises_and_restores_the_playhead(self):
        # Arrange
        self.timeline.timecode = "02:00:00:00"

        # Act & Assert
        with self.assertRaises(WorkflowError):
            run(self.resolve, self.options)
        self.assertEqual("02:00:00:00", self.timeline.GetCurrentTimecode())

    def test_given_look_mode_without_an_image_when_running_then_raises(self):
        # Arrange
        options = replace(self.options, mode="look", reference_image=os.path.join(self.folder.name, "missing.png"))

        # Act & Assert
        with self.assertRaises(WorkflowError):
            run(self.resolve, options)

    def test_given_an_empty_track_when_running_then_raises(self):
        # Arrange
        options = replace(self.options, track_index=2)

        # Act & Assert
        with self.assertRaisesRegex(WorkflowError, "V2"):
            run(self.resolve, options)

    def test_given_no_open_project_when_running_then_raises(self):
        # Arrange
        resolve = FakeResolve(None)

        # Act & Assert
        with self.assertRaises(WorkflowError):
            run(resolve, self.options)

    def test_given_resolve_rejects_a_lut_when_applying_then_that_clip_is_reported_as_not_applied(self):
        # Arrange
        self.graphs[2].accepts_lut = False

        # Act
        results = run(self.resolve, self.options)

        # Assert
        self.assertEqual([True, False], [result.applied for result in results])
        self.assertIn("rutas de LUT", results[1].message)

    def test_given_one_still_export_fails_when_matching_then_other_clips_are_still_graded(self):
        # Arrange
        self.project.failing_items = {"a"}

        # Act
        results = run(self.resolve, self.options)

        # Assert
        self.assertEqual([("Plano A", False), ("Plano B", True)], [(result.name, result.applied) for result in results])

    def test_given_unsafe_clip_names_when_naming_the_lut_then_the_file_name_is_safe(self):
        # Act
        name = lut_file_name("Escena: 1/2", 7, 'A001 "toma" *final*', "20261112-101500")

        # Assert
        self.assertEqual("Escena_1_2_007_A001_toma_final_20261112-101500.cube", name)
