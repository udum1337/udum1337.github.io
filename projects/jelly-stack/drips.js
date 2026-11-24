/* DripField — оторванные куски желе.
 *
 * Когда желешка садится неровно, лишняя часть не рассыпается мелкими
 * каплями, а отрывается одним куском:
 *
 *   1) висит на кромке, вытягиваясь вниз и утончая шейку;
 *   2) шейка рвётся — кусок падает как цельная желешка;
 *   3) в полёте он вытягивается от скорости и покачивается.
 *
 * Всё рисуется в одном Graphics: один объект на весь слой.
 */

class DripField {
  constructor(scene) {
    this.scene = scene;
    this.graphics = scene.add.graphics();
    this.graphics.setDepth(2); // выше башни, но ниже падающей желешки
    this.items = [];
  }

  // x, y — точка на кромке желешки; dir — наружу; size — сколько отвалилось
  tear(x, y, color, dir, size) {
    const w = Phaser.Math.Clamp(size * 0.6, 14, 42);

    this.items.push({
      x: x,
      y: y,
      color: color,
      dir: dir,
      w: w,
      h: w * Phaser.Math.FloatBetween(1.0, 1.15),
      t: 0,
      hang: Phaser.Math.FloatBetween(0.28, 0.4), // сколько тянется шейка
      stage: 'hang',
      vx: 0,
      vy: 0,
      rw: w * 0.5,     // половина ширины тела (для плавного перехода)
      rh: w * 0.5,     // половина высоты тела
      cx: x,
      cy: y,
      life: 1.5,
      alpha: 1,
      phase: Math.random() * Math.PI * 2
    });
  }

  update(dt) {
    const g = this.graphics;
    g.clear();

    if (!this.items.length) return;

    const alive = [];

    for (let i = 0; i < this.items.length; i++) {
      const d = this.items[i];
      d.t += dt;

      if (d.stage === 'hang') {
        this.drawHang(d);

        if (d.t >= d.hang) {
          // шейка лопнула: дальше кусок летит из того места, где висело тело
          d.stage = 'fall';
          d.t = 0;
          d.x = d.cx;
          d.y = d.cy;
          d.vy = 40;
          d.vx = d.dir * Phaser.Math.FloatBetween(4, 22);
          SFX.drip();
        }

        alive.push(d);
        continue;
      }

      // --- падение цельным куском ---
      d.vy += 1600 * dt;
      d.x += d.vx * dt;
      d.y += d.vy * dt;

      if (d.t > d.life) continue;

      d.alpha = Math.min(1, Math.max(0, (d.life - d.t) / 0.3));
      this.drawFall(d);

      alive.push(d);
    }

    this.items = alive;
  }

  // висящий кусок: тело + сужающаяся шейка к кромке
  drawHang(d) {
    const g = this.graphics;
    const p = Math.min(1, d.t / d.hang);
    const sag = p * p; // сначала медленно, потом всё быстрее

    const neckLen = d.h * (0.1 + 0.55 * sag);   // шея тянется вниз
    const neckW = d.w * (0.42 - 0.38 * sag);    // и утончается почти в нить
    const bx = d.x + d.dir * d.w * 0.18 * sag;
    const bw = d.w * (0.5 + 0.02 * sag);
    const bh = d.h * (0.5 + 0.1 * sag);
    const by = d.y + neckLen + bh * 0.92;

    // запоминаем размеры тела: в момент разрыва кусок стартует ровно таким
    d.cx = bx;
    d.cy = by;
    d.rw = bw;
    d.rh = bh;

    const pts = [{ x: d.x - neckW, y: d.y }];

    // низ тела: почти полная дуга — тело остаётся круглым комком
    const N = 20;
    const a0 = Math.PI * 1.22;
    const a1 = -Math.PI * 0.22;
    for (let i = 0; i <= N; i++) {
      const a = a0 + (a1 - a0) * (i / N);
      pts.push({ x: bx + Math.cos(a) * bw, y: by + Math.sin(a) * bh });
    }

    pts.push({ x: d.x + neckW, y: d.y });

    g.fillStyle(d.color, 0.98);
    g.fillPoints(pts, true);

    // блик
    g.fillStyle(0xffffff, 0.26);
    g.fillEllipse(bx - bw * 0.3, by - bh * 0.1, bw * 0.7, bh * 0.45);
  }

  // упавший кусок: вытягивается по скорости, покачивается
  drawFall(d) {
    const g = this.graphics;

    const stretch = 1 + Math.min(d.vy / 1500, 1.05);
    const rx = d.rw / Math.sqrt(stretch);
    const ry = d.rh * Math.sqrt(stretch);
    const wobble = 0.05 * Math.sin(d.t * 15 + d.phase);

    const pts = [];
    const N = 22;
    for (let i = 0; i < N; i++) {
      const a = (i / N) * Math.PI * 2;
      const k = 1 + wobble * Math.sin(a * 3 + d.phase);
      pts.push({
        x: d.x + Math.cos(a) * rx * k,
        y: d.y + Math.sin(a) * ry * k
      });
    }

    g.fillStyle(d.color, 0.97 * d.alpha);
    g.fillPoints(pts, true);

    g.fillStyle(0xffffff, 0.28 * d.alpha);
    g.fillEllipse(d.x - rx * 0.3, d.y - ry * 0.12, rx * 0.7, ry * 0.4);
  }

  clear() {
    this.items = [];
    this.graphics.clear();
  }
}
