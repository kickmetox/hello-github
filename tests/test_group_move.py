import unittest

from officedisplay.model.presentation import Slide, SlideObject, flatten, group_objects, move_object_to_slide, ungroup


class GroupMoveTest(unittest.TestCase):
    def test_group_move_ungroup_and_slide(self):
        slide = Slide(id="s1", name="Eins")
        slide.objects = [
            SlideObject(id="a", kind="shape", x=0.1, y=0.1, w=0.2, h=0.1, name="A"),
            SlideObject(id="b", kind="shape", x=0.4, y=0.3, w=0.2, h=0.1, name="B"),
        ]
        group = group_objects(slide, ["a", "b"])
        self.assertIsNotNone(group)
        self.assertEqual(len(slide.objects), 1)
        group.x += 0.05
        group.y += 0.05
        placed = {obj.id: (x, y) for obj, x, y, _w, _h in flatten(slide)}
        self.assertAlmostEqual(placed["a"][0], 0.15)
        self.assertAlmostEqual(placed["a"][1], 0.15)
        released = ungroup(slide, group.id)
        self.assertEqual(len(released), 2)
        self.assertAlmostEqual(released[0].x, 0.15)
        other = Slide(id="s2", name="Zwei")
        self.assertTrue(move_object_to_slide(slide, other, released[0].id))
        self.assertEqual([obj.id for obj in other.objects], [released[0].id])
        self.assertNotIn(released[0].id, [obj.id for obj in slide.objects])


if __name__ == "__main__":
    unittest.main()
