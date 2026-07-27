"""Tests for physics.collision: AABB math, layers, move-and-slide (Phase 3)."""

from __future__ import annotations

from physics.collision import AABB, CollisionLayer, CollisionWorld, StaticCollider

WALL = CollisionLayer.WORLD


def test_aabb_intersects_on_overlap() -> None:
    a = AABB(0.0, 0.0, 10.0, 10.0)
    assert a.intersects(AABB(5.0, 5.0, 10.0, 10.0))


def test_aabb_touching_edges_do_not_intersect() -> None:
    a = AABB(0.0, 0.0, 10.0, 10.0)
    assert not a.intersects(AABB(10.0, 0.0, 10.0, 10.0))
    assert not a.intersects(AABB(0.0, 10.0, 10.0, 10.0))


def test_aabb_separated_does_not_intersect() -> None:
    a = AABB(0.0, 0.0, 10.0, 10.0)
    assert not a.intersects(AABB(20.0, 20.0, 5.0, 5.0))


def test_aabb_derived_geometry() -> None:
    box = AABB(10.0, 20.0, 8.0, 6.0)
    assert (box.left, box.right, box.top, box.bottom) == (10.0, 18.0, 20.0, 26.0)
    assert box.center == (14.0, 23.0)
    assert box.moved(1.0, -2.0).x == 11.0
    assert box.moved(1.0, -2.0).y == 18.0


def test_query_filters_by_layer() -> None:
    world = CollisionWorld(
        [
            StaticCollider(AABB(0.0, 0.0, 10.0, 10.0), WALL),
            StaticCollider(AABB(2.0, 2.0, 10.0, 10.0), CollisionLayer.ENEMY_BODY),
        ]
    )
    everything = world.query(AABB(1.0, 1.0, 4.0, 4.0))
    assert len(everything) == 2
    world_only = world.query(AABB(1.0, 1.0, 4.0, 4.0), layers=[WALL])
    assert [c.layer for c in world_only] == [WALL]


def test_move_and_slide_free_space_moves_fully() -> None:
    world = CollisionWorld()
    result = world.move_and_slide(AABB(0.0, 0.0, 10.0, 10.0), 5.0, -3.0)
    assert result.box.x == 5.0
    assert result.box.y == -3.0
    assert not result.hit_x
    assert not result.hit_y


def test_move_and_slide_stops_at_wall_edge() -> None:
    world = CollisionWorld([StaticCollider(AABB(20.0, 0.0, 10.0, 50.0), WALL)])
    result = world.move_and_slide(AABB(0.0, 0.0, 10.0, 10.0), 30.0, 0.0)
    assert result.hit_x
    assert result.box.right == 20.0  # flush against the wall, no tunneling
    assert not result.hit_y


def test_move_and_slide_slides_along_wall_on_other_axis() -> None:
    world = CollisionWorld([StaticCollider(AABB(20.0, 0.0, 10.0, 50.0), WALL)])
    result = world.move_and_slide(AABB(15.0, 0.0, 10.0, 10.0), 10.0, 5.0)
    assert result.hit_x
    assert result.box.right == 20.0
    assert result.box.y == 5.0  # vertical motion preserved (sliding)
    assert not result.hit_y


def test_move_and_slide_respects_layer_filter() -> None:
    ghost_layer = CollisionLayer.ENEMY_BODY
    world = CollisionWorld([StaticCollider(AABB(20.0, 0.0, 10.0, 50.0), ghost_layer)])
    result = world.move_and_slide(AABB(0.0, 0.0, 10.0, 10.0), 30.0, 0.0)
    assert not result.hit_x  # filtered out: passes through
    assert result.box.x == 30.0


def test_move_and_slide_resolves_against_multiple_colliders() -> None:
    world = CollisionWorld(
        [
            StaticCollider(AABB(30.0, -10.0, 10.0, 20.0), WALL),
            StaticCollider(AABB(20.0, 10.0, 30.0, 10.0), WALL),
        ]
    )
    result = world.move_and_slide(AABB(0.0, 0.0, 10.0, 10.0), 40.0, 40.0)
    assert result.hit_x and result.hit_y
    assert not any(
        result.box.intersects(c.box) for c in world.query(result.box)
    )


def test_add_box_registers_collider() -> None:
    world = CollisionWorld()
    world.add_box(1.0, 2.0, 3.0, 4.0)
    assert len(world.colliders) == 1
    assert world.colliders[0].box == AABB(1.0, 2.0, 3.0, 4.0)
    world.clear()
    assert world.colliders == ()
