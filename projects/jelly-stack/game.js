/* Jelly Stack
 *
 * Механика:
 *   - сверху ездит носик с желешкой;
 *   - тап/пробел — желешка падает;
 *   - мягкое тело деформируется пружинами при ударе;
 *   - лишняя часть отрывается цельным куском и падает, растягиваясь;
 *   - башня кренится от смещённого центра масс и может рухнуть.
 *
 * Файлы: sfx.js (звук), jelly.js (мягкое тело), drips.js (оторванные
 * куски), game.js (игра).
 */

const W = 480;
const H = 800;

const BASE_Y = 1400;        // мировая Y основания башни
const BLOB_H = 36;          // высота желешки
const BASE_W = 240;         // ширина основания
const MIN_W = 48;           // меньше — промах
const GRAVITY = 2600;       // px/сек^2
const START_SCROLL = 680;   // начальный сдвиг камеры
const DROP_SCREEN_Y = 104;  // экранная Y, откуда падает желе
const STEP = 1 / 120;       // фиксированный шаг физики
const LEAN_LIMIT = 0.52;    // при каком смещении центра масс башня падает
const RECORD_KEY = 'jelly-stack-record';

const COLORS = [0xff7a9a, 0xffb35c, 0xffe066, 0x7be495, 0x5cc9ff, 0xb18cff];
const NOTES = [261.63, 293.66, 329.63, 392.0, 440.0]; // пентатоника C
const FONT = '"Segoe UI", system-ui, -apple-system, sans-serif';

// ---------------------------------------------------------------------------
// Рекорд
// ---------------------------------------------------------------------------
function loadRecord() {
  try {
    return parseInt(window.localStorage.getItem(RECORD_KEY) || '0', 10) || 0;
  } catch (e) {
    return 0;
  }
}

function saveRecord(value) {
  try {
    window.localStorage.setItem(RECORD_KEY, String(value));
  } catch (e) {
    /* приватный режим — переживём */
  }
}

// ---------------------------------------------------------------------------
// Boot: генерируем текстуры кодом
// ---------------------------------------------------------------------------
class BootScene extends Phaser.Scene {
  constructor() {
    super('Boot');
  }

  create() {
    const g = this.make.graphics({ x: 0, y: 0, add: false });

    g.fillStyle(0xffffff, 1);
    g.fillRoundedRect(0, 0, 200, 64, 32);
    g.generateTexture('jelly', 200, 64);

    g.destroy();
    this.scene.start('Game');
  }
}

// ---------------------------------------------------------------------------
// Игра
// ---------------------------------------------------------------------------
class GameScene extends Phaser.Scene {
  constructor() {
    super('Game');
  }

  create() {
    this.isOver = false;
    this.canRestart = false;
    this.body = null;         // активная падающая желешка
    this.fallingBody = null;  // та, что улетает вниз (после промаха)
    this.acc = 0;
    this.settle = 0;
    this.squash = [];         // желешки, которые ещё пружинят после посадки

    this.tower = [];
    this.score = 0;
    this.dropSpeed = 190;
    this.dropDir = 1;
    this.colorIndex = 1;
    this.record = loadRecord();

    this.cameras.main.setScroll(0, START_SCROLL);

    this.createBackground();

    // контейнер башни: наклоняется вокруг основания
    this.world = this.add.container(W / 2, BASE_Y);
    this.world.setDepth(0);

    const shadow = this.add.ellipse(0, 6, 330, 28, 0x000000, 0.28);
    this.world.add(shadow);

    const base = this.addJelly(W / 2, BASE_Y - BLOB_H / 2, BASE_W, COLORS[0], true);
    this.tower.push(base);
    this.towerTopY = BASE_Y - BLOB_H;

    this.createDropper();
    this.createUi();
    this.drips = new DripField(this);
    this.refreshPreview();

    this.input.on('pointerdown', (p) => this.handleTap(p));
    this.input.keyboard.on('keydown-SPACE', () => this.handleTap());
    this.input.keyboard.on('keydown-ENTER', () => this.handleTap());
  }

  // --- создание -----------------------------------------------------------

  createBackground() {
    const bg = this.add.graphics();
    bg.fillGradientStyle(0x26263c, 0x26263c, 0x0b0b14, 0x0b0b14, 1);
    bg.fillRect(0, 0, W, H);
    bg.setScrollFactor(0);
    bg.setDepth(-10);
  }

  createDropper() {
    this.dropper = this.add.container(W / 2, 70);
    this.dropper.setScrollFactor(0, true);
    this.dropper.setDepth(5);

    const rod = this.add.rectangle(0, -18, 10, 36, 0xffffff, 0.3);
    const tip = this.add.ellipse(0, 0, 18, 8, 0xffffff, 0.75);
    this.dropper.add([rod, tip]);

    this.preview = this.add.image(W / 2, DROP_SCREEN_Y, 'jelly');
    this.preview.setScrollFactor(0);
    this.preview.setDepth(4);
    this.preview.setAlpha(0.95);
  }

  createUi() {
    this.scoreText = this.add.text(W / 2, 34, '0', {
      fontFamily: FONT,
      fontSize: '42px',
      fontStyle: 'bold',
      color: '#ffffff'
    });
    this.scoreText.setOrigin(0.5);
    this.scoreText.setScrollFactor(0);
    this.scoreText.setDepth(10);

    this.recordText = this.add.text(22, 34, 'РЕКОРД ' + this.record, {
      fontFamily: FONT,
      fontSize: '15px',
      color: '#9a9ab0'
    });
    this.recordText.setOrigin(0, 0.5);
    this.recordText.setScrollFactor(0);
    this.recordText.setDepth(10);

    this.soundText = this.add.text(W - 34, 30, '♪', {
      fontFamily: FONT,
      fontSize: '30px',
      color: '#ffffff'
    });
    this.soundText.setOrigin(0.5);
    this.soundText.setScrollFactor(0);
    this.soundText.setDepth(10);
    this.soundText.setAlpha(SFX.muted ? 0.25 : 0.85);

    this.hint = this.add.text(W / 2, H - 44, 'Тапни, чтобы уронить желе', {
      fontFamily: FONT,
      fontSize: '19px',
      color: '#ffffff'
    });
    this.hint.setOrigin(0.5);
    this.hint.setScrollFactor(0);
    this.hint.setDepth(10);
    this.hint.setAlpha(0.55);

    this.tweens.add({
      targets: this.hint,
      alpha: 0.15,
      duration: 900,
      yoyo: true,
      repeat: -1
    });
  }

  addJelly(x, y, w, color, isBase) {
    const rx = x - this.world.x;
    const ry = y - this.world.y;

    const sprite = this.add.image(rx, ry, 'jelly');
    sprite.setDisplaySize(w, BLOB_H);
    sprite.setTint(color);
    sprite.setAlpha(isBase ? 1 : 0.96);

    const gloss = this.add.ellipse(
      rx - w * 0.17,
      ry - BLOB_H * 0.24,
      w * 0.42,
      9,
      0xffffff,
      0.3
    );

    this.world.add([sprite, gloss]);

    return {
      x: x,
      y: y,
      w: w,
      color: color,
      sprite: sprite,
      gloss: gloss,
      baseSX: sprite.scaleX,
      baseSY: sprite.scaleY,
      baseY: ry,
      glossY: gloss.y
    };
  }

  // --- управление ---------------------------------------------------------

  handleTap(pointer) {
    // кнопка звука в правом верхнем углу
    if (pointer && pointer.y < 80 && pointer.x > W - 90) {
      this.toggleSound();
      return;
    }

    SFX.init();

    if (this.isOver) {
      if (this.canRestart) this.scene.restart();
      return;
    }

    this.drop();
  }

  toggleSound() {
    SFX.init();
    const muted = SFX.toggle();
    this.soundText.setAlpha(muted ? 0.25 : 0.85);
  }

  drop() {
    if (this.body) return;

    const top = this.tower[this.tower.length - 1];
    const color = COLORS[this.colorIndex % COLORS.length];
    const x = this.dropper.x;
    const y = this.cameras.main.scrollY + DROP_SCREEN_Y;

    const body = new JellyBody(this, x, y, top.w, BLOB_H, color);
    body.startX = x;
    body.w = top.w;

    this.body = body;
    this.acc = 0;
    this.settle = 0;

    this.preview.setVisible(false);
    this.hint.setVisible(false);
  }

  moveDropper(dt) {
    const range = this.getDropRange();

    this.dropper.x += this.dropDir * this.dropSpeed * dt;

    if (this.dropper.x >= range.max) {
      this.dropper.x = range.max;
      this.dropDir = -1;
    } else if (this.dropper.x <= range.min) {
      this.dropper.x = range.min;
      this.dropDir = 1;
    }

    this.preview.x = this.dropper.x;
  }

  getDropRange() {
    const top = this.tower[this.tower.length - 1];
    const half = top.w / 2;
    const pad = Math.max(18, half * 0.12);

    return { min: half + pad, max: W - half - pad };
  }

  // --- физика падения -----------------------------------------------------

  updateBody(dt) {
    const body = this.body;
    const top = this.tower[this.tower.length - 1];
    const surface = {
      y: this.towerTopY,
      left: top.x - top.w / 2,
      right: top.x + top.w / 2
    };

    this.acc += dt;
    let steps = 0;
    while (this.acc >= STEP && steps < 4) {
      body.step(STEP, GRAVITY, surface);
      this.acc -= STEP;
      steps += 1;
    }

    if (body.contact > 0) {
      this.settle += dt;
    }

    if (this.settle > 0.3) {
      this.finishDrop();
    } else if (body.y > this.towerTopY + 600) {
      this.finishDrop();
    }
  }

  finishDrop() {
    const body = this.body;
    this.body = null;
    this.acc = 0;
    this.settle = 0;

    const top = this.tower[this.tower.length - 1];
    const bodyLeft = body.startX - body.w / 2;
    const bodyRight = body.startX + body.w / 2;
    const left = Math.max(bodyLeft, top.x - top.w / 2);
    const right = Math.min(bodyRight, top.x + top.w / 2);
    const overlap = right - left;

    // совсем мимо: желе улетает вниз и растворяется
    if (overlap < MIN_W) {
      this.fallingBody = body;
      this.missDrop();
      return;
    }

    // запоминаем, в каком состоянии пружина в момент передачи в башню
    const sy0 = body.sy;
    const syv0 = body.syVel;

    body.destroy();

    // лишнее отрывается цельным куском: слева и/или справа
    const overLeft = left - bodyLeft;
    const overRight = bodyRight - right;
    if (overLeft > 2) this.spawnDrips(left, body.color, -1, overLeft);
    if (overRight > 2) this.spawnDrips(right, body.color, 1, overRight);

    const newX = (left + right) / 2;
    const lost = body.w - overlap;

    const blob = this.addJelly(newX, this.towerTopY - BLOB_H / 2, overlap, body.color, false);
    this.tower.push(blob);
    this.towerTopY -= BLOB_H;

    this.score += 1;
    this.colorIndex += 1;
    this.dropSpeed = Math.min(this.dropSpeed + 9, 430);

    this.scoreText.setText(String(this.score));
    this.tweens.add({
      targets: this.scoreText,
      scale: { from: 1.35, to: 1 },
      duration: 260,
      ease: 'Back.easeOut'
    });

    SFX.plop(this.noteFor(this.score));

    // сжатие продолжается на уже лежащей желешке — без рывка
    this.startSquash(blob, sy0, syv0);

    this.cameras.main.shake(70, 0.0015);

    if (lost < 6) {
      this.perfectHit(newX, this.towerTopY + BLOB_H);
    }

    this.updateLean();
    if (this.leanRatio > 0.4) SFX.creak();
    this.refreshPreview();
  }

  noteFor(n) {
    const octave = Math.min(1, Math.floor(n / NOTES.length));
    return NOTES[n % NOTES.length] * Math.pow(2, octave);
  }

  perfectHit(x, y) {
    const label = this.add.text(x, y, 'ИДЕАЛЬНО', {
      fontFamily: FONT,
      fontSize: '20px',
      fontStyle: 'bold',
      color: '#ffffff'
    });
    label.setOrigin(0.5);
    label.setDepth(6);

    this.tweens.add({
      targets: label,
      y: y - 70,
      alpha: 0,
      duration: 800,
      ease: 'Quad.easeOut',
      onComplete: () => label.destroy()
    });

    SFX.perfect();
    this.cameras.main.flash(90, 255, 255, 255);
  }

  spawnDrips(x, color, dir, size) {
    this.drips.tear(x, this.towerTopY - BLOB_H * 0.45, color, dir, size);
  }

  // --- сжатие лежащей желешки ---------------------------------------------
  // Та же пружина, что была у падающего тела: подхватываем её состояние,
  // поэтому на стыке нет ни скачка, ни рывка.

  startSquash(blob, s, v) {
    blob.sq = s;
    blob.sqVel = v;
    this.squash.push(blob);
    this.applySquash(blob);
  }

  applySquash(blob) {
    const s = blob.sq;
    const sx = 1 + (1 - s) * 0.6;
    const dy = (BLOB_H / 2) * (1 - s); // низ остаётся на поверхности

    blob.sprite.scaleX = blob.baseSX * sx;
    blob.sprite.scaleY = blob.baseSY * s;
    blob.sprite.y = blob.baseY + dy;

    blob.gloss.scaleX = sx;
    blob.gloss.scaleY = s;
    blob.gloss.y = blob.glossY + dy;
  }

  stepSquash(dt) {
    if (!this.squash.length) return;

    const alive = [];

    for (let i = 0; i < this.squash.length; i++) {
      const blob = this.squash[i];

      blob.sqVel += (-SQUASH_K * (blob.sq - 1) - SQUASH_DAMP * blob.sqVel) * dt;
      blob.sq += blob.sqVel * dt;

      if (Math.abs(blob.sq - 1) < 0.004 && Math.abs(blob.sqVel) < 0.08) {
        blob.sq = 1;
        blob.sqVel = 0;
        this.applySquash(blob);
        continue;
      }

      this.applySquash(blob);
      alive.push(blob);
    }

    this.squash = alive;
  }

  refreshPreview() {
    const top = this.tower[this.tower.length - 1];
    const color = COLORS[this.colorIndex % COLORS.length];

    this.preview.setDisplaySize(top.w, BLOB_H);
    this.preview.setTint(color);
    this.preview.x = this.dropper.x;
    this.preview.setVisible(!this.isOver);
  }

  // --- наклон и обрушение -------------------------------------------------

  updateLean() {
    // взвешенный центр масс: верхние желешки влияют сильнее (высокая башня менее устойчива)
    let sum = 0;
    let wsum = 0;
    for (let i = 0; i < this.tower.length; i++) {
      const wgt = 1 + i * 0.25;
      sum += this.tower[i].x * wgt;
      wsum += wgt;
    }
    const comX = sum / wsum;
    const offset = comX - W / 2;
    const ratio = Math.abs(offset) / (BASE_W / 2);
    const dir = offset >= 0 ? 1 : -1;

    this.leanRatio = ratio;

    // короткий качок вместо постоянного крена: прицел не сбивается
    const kick = (0.8 + ratio * 7) * dir;
    this.tweens.killTweensOf(this.world);
    this.world.setAngle(0);
    this.tweens.add({
      targets: this.world,
      angle: kick,
      duration: 90,
      yoyo: true,
      ease: 'Sine.easeInOut'
    });

    if (ratio > LEAN_LIMIT) {
      this.collapse(dir);
    }
  }

  collapse(dir) {
    if (this.isOver) return;

    this.isOver = true;
    this.preview.setVisible(false);
    SFX.collapse();
    this.cameras.main.shake(700, 0.012);

    this.tweens.add({
      targets: this.world,
      angle: dir * 82,
      duration: 850,
      ease: 'Cubic.easeIn'
    });

    this.time.delayedCall(900, () => this.showOverlay('БАШНЯ УПАЛА'));
  }

  missDrop() {
    if (this.isOver) return;

    this.isOver = true;
    this.preview.setVisible(false);
    SFX.gameOver();

    this.time.delayedCall(420, () => this.showOverlay('МИМО'));
  }

  // --- экран конца игры ---------------------------------------------------

  showOverlay(title) {
    const isRecord = this.score > this.record;
    if (isRecord) {
      this.record = this.score;
      saveRecord(this.record);
      this.recordText.setText('РЕКОРД ' + this.record);
    }

    const dim = this.add.rectangle(W / 2, H / 2, W, H, 0x05050a, 0.75);
    dim.setScrollFactor(0);
    dim.setDepth(20);

    this.add.text(W / 2, H / 2 - 150, title, {
      fontFamily: FONT,
      fontSize: '50px',
      fontStyle: 'bold',
      color: '#ff7a9a'
    }).setOrigin(0.5).setScrollFactor(0).setDepth(21);

    this.add.text(W / 2, H / 2 - 70, 'Высота: ' + this.score, {
      fontFamily: FONT,
      fontSize: '32px',
      color: '#ffffff'
    }).setOrigin(0.5).setScrollFactor(0).setDepth(21);

    this.add.text(W / 2, H / 2 - 20, isRecord ? 'НОВЫЙ РЕКОРД!' : 'Рекорд: ' + this.record, {
      fontFamily: FONT,
      fontSize: '20px',
      color: isRecord ? '#ffe066' : '#9a9ab0'
    }).setOrigin(0.5).setScrollFactor(0).setDepth(21);

    const again = this.add.text(W / 2, H / 2 + 80, 'Тапни, чтобы сыграть снова', {
      fontFamily: FONT,
      fontSize: '21px',
      color: '#ffffff'
    }).setOrigin(0.5).setScrollFactor(0).setDepth(21).setAlpha(0.85);

    this.tweens.add({
      targets: again,
      alpha: 0.25,
      duration: 700,
      yoyo: true,
      repeat: -1
    });

    this.time.delayedCall(500, () => {
      this.canRestart = true;
    });
  }

  // --- главный цикл -------------------------------------------------------

  update(time, delta) {
    const dt = Math.min(delta, 32) / 1000;

    this.drips.update(dt);
    this.stepSquash(dt);

    if (this.body) {
      this.updateBody(dt);
    } else if (!this.isOver) {
      this.moveDropper(dt);
    }

    // желе, улетевшее мимо, продолжает падать и таять
    if (this.fallingBody) {
      const fb = this.fallingBody;
      fb.step(STEP, GRAVITY, null);
      fb.graphics.setAlpha(Math.max(0, fb.graphics.alpha - dt * 1.1));
      if (fb.graphics.alpha <= 0) {
        fb.destroy();
        this.fallingBody = null;
      }
    }

    const target = Math.min(START_SCROLL, this.towerTopY - 200);
    this.cameras.main.scrollY = Phaser.Math.Linear(this.cameras.main.scrollY, target, 0.08);
  }
}

// ---------------------------------------------------------------------------
// Запуск
// ---------------------------------------------------------------------------
window.game = new Phaser.Game({
  type: Phaser.AUTO,
  parent: 'game',
  width: W,
  height: H,
  backgroundColor: '#0b0b14',
  scale: {
    mode: Phaser.Scale.FIT,
    autoCenter: Phaser.Scale.CENTER_BOTH
  },
  scene: [BootScene, GameScene]
});
