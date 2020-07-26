import wasabi2d as w2d
import random
from pygame.math import Vector2
from wasabi2d.keyboard import keys


mode_1080p = 1920, 1080
scene = w2d.Scene(
    *mode_1080p,
    fullscreen=True,
    background='#444455'
)
scene.layers[0].set_effect('dropshadow', opacity=0.5)
center = Vector2(scene.width, scene.height) / 2

red_score = scene.layers[-1].add_label(
    0,
    pos=(30, 100),
    font="bitwise",
    fontsize=100,
    align="left",
    color='red'
)

blue_score = scene.layers[-1].add_label(
    0,
    pos=(scene.width, 100),
    font="bitwise",
    fontsize=100,
    align="right",
    color='cyan'
)

red = scene.layers[0].add_sprite(
    'bat_red',
    pos=(50, center.y)
)
red.up_key = keys.Q
red.down_key = keys.A

blue = scene.layers[0].add_sprite(
    'bat_blue',
    pos=(scene.width - 50, center.y)
)
blue.up_key = keys.I
blue.down_key = keys.K

ball = scene.layers[0].add_sprite(
    'ball',
    pos=center
)

SPEED = 1000
BALL_RADIUS = ball.width / 2


def start():
    ball.pos = center
    ball.vel = Vector2(
        random.choice([SPEED, -SPEED]),
        random.uniform(SPEED, -SPEED),
    )


def collide_bat(bat):
    bounds = bat.bounds.inflate(BALL_RADIUS, BALL_RADIUS)
    if bounds.collidepoint(ball.pos):
        x, y = ball.pos
        vx, vy = ball.vel
        if x < bat.x:
            ball.vel = Vector2(-abs(vx), vy)
        else:
            ball.vel = Vector2(abs(vx), vy)


@w2d.event
def update(dt, keyboard):
    ball.pos += ball.vel * dt
    x, y = ball.pos
    if y < BALL_RADIUS:
        ball.vel.y = abs(ball.vel.y)
    elif y > scene.height - BALL_RADIUS:
        ball.vel.y = -abs(ball.vel.y)

    if x < -BALL_RADIUS:
        scene.camera.screen_shake()
        blue_score.text += 1
        start()
    elif x > scene.width + BALL_RADIUS:
        start()
        scene.camera.screen_shake()
        red_score.text += 1

    for bat in (red, blue):
        if keyboard[bat.up_key]:
            bat.y -= SPEED * dt
        elif keyboard[bat.down_key]:
            bat.y += SPEED * dt

        collide_bat(bat)


start()
w2d.run()