"""
Meat netting applicator (Browin 310090 style) for Fusion 360.

Creates a new design with one body: a tube with a bell-mouth entry, a round
flange cut flat at the bottom, and a flat foot under the tube.

Use on a counter: stand it on the foot with the flange flush to the counter
edge, mouth facing you, and clamp the two foot "ears" down with small C-clamps.
Bunch the netting on the OUTSIDE of the tube, push the meat into the mouth,
and it comes out the far end netted, onto the counter.

Print it mouth-down (flange flat on the bed): every surface then overhangs
45 deg or less, so it needs no supports. Footprint is about 172 x 160 mm, 156 mm tall.

Coordinates: Z is the tube axis, Z=0 is the mouth (back face of the flange),
the tube points toward +Z, -Y is down (the counter). Dimensions are in mm.
Edit the values, then re-run the script (it makes a fresh document each time).
"""

import adsk.core
import adsk.fusion
import traceback

# ---------------- Parameters (mm) ----------------
BORE_D = 100.0     # inside diameter the meat passes through
WALL = 3.0         # tube wall thickness
TUBE_LEN = 150.0   # tube length in front of the flange (holds the bunched netting)
ENTRY_R = 12.0     # radius of the bell-mouth entry
TIP_LEN = 8.0      # length of the outer taper at the exit lip
TIP_IN = 1.5       # how much the wall thins at the exit lip (net slides off cleanly)

FLANGE_D = 172.0   # round flange diameter
FLANGE_T = 6.0     # flange thickness
HUB = 4.0          # extra material around the bell mouth

BASE = 74.0        # tube axis height above the counter (flange is cut flat here)
FOOT_T = 6.0       # foot thickness
FOOT_W = 150.0     # foot width; the ears beyond the flange are where the clamps go
FOOT_LEN = 110.0   # how far the foot runs under the tube
FOOT_R = 50.0      # front corner radius of the foot
WEB_T = 8.0        # web joining the foot to the underside of the tube
WEB_LEN = 40.0
EAR_HOLE_D = 5.0   # optional screw holes in the ears, for permanent mounting
# --------------------------------------------------


def mm(v):
    return v / 10.0  # Fusion API works in cm


def run(context):
    ui = None
    try:
        app = adsk.core.Application.get()
        ui = app.userInterface
        app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        design = adsk.fusion.Design.cast(app.activeProduct)
        root = design.rootComponent
        sketches = root.sketches
        extrudes = root.features.extrudeFeatures
        VI = adsk.core.ValueInput
        Op = adsk.fusion.FeatureOperations

        def sp(sk, x, y, z):
            # model mm -> sketch space, so every plane's axis quirks are handled
            return sk.modelToSketchSpace(adsk.core.Point3D.create(mm(x), mm(y), mm(z)))

        def poly(sk, pts, close=True):
            lines = sk.sketchCurves.sketchLines
            first = lines.addByTwoPoints(sp(sk, *pts[0]), sp(sk, *pts[1]))
            prev = first
            for p in pts[2:]:
                prev = lines.addByTwoPoints(prev.endSketchPoint, sp(sk, *p))
            if close:
                lines.addByTwoPoints(prev.endSketchPoint, first.startSketchPoint)
            return first, prev

        def extrude(prof, dist, op, symmetric=False, bodies=None):
            inp = extrudes.createInput(prof, op)
            if symmetric:
                inp.setSymmetricExtent(VI.createByReal(mm(dist)), True)
            else:
                inp.setDistanceExtent(False, VI.createByReal(mm(dist)))
            if bodies:
                inp.participantBodies = bodies
            return extrudes.add(inp)

        def offset_plane(base, dist):
            pin = root.constructionPlanes.createInput()
            pin.setByOffset(base, VI.createByReal(mm(dist)))
            return root.constructionPlanes.add(pin)

        Ri = BORE_D / 2
        Ro = Ri + WALL
        Rc = Ri + ENTRY_R + HUB
        H = ENTRY_R + 3          # hub height before it tapers into the tube
        T = FLANGE_T + TUBE_LEN
        Rf = FLANGE_D / 2
        k = 0.70710678

        # 1. Tube with bell mouth: revolve a half cross-section (r, z) around Z
        sk = sketches.add(root.xZConstructionPlane)
        sk.name = 'Tube profile'
        # Bell mouth: an arc tangent to the bore that turns until it is at 45 deg,
        # then a 45 deg flare to the face, so printed mouth-down it never
        # overhangs more than 45 deg and needs no supports.
        m = ENTRY_R * (1 - k)
        tube_pts = [
            (Ri + m, m), (Ri + 2 * m, 0), (Rc, 0), (Rc, H), (Ro, H + Rc - Ro),
            (Ro, T - TIP_LEN), (Ro - TIP_IN, T),
            (Ri, T), (Ri, ENTRY_R),
        ]
        first, last = poly(sk, [(r, 0, z) for r, z in tube_pts], close=False)
        sk.sketchCurves.sketchArcs.addByThreePoints(
            last.endSketchPoint,
            sp(sk, Ri + ENTRY_R * (1 - 0.92388), 0, ENTRY_R * (1 - 0.38268)),
            first.startSketchPoint)
        axis = sk.sketchCurves.sketchLines.addByTwoPoints(sp(sk, 0, 0, 0), sp(sk, 0, 0, T))
        axis.isConstruction = True
        revolves = root.features.revolveFeatures
        rin = revolves.createInput(sk.profiles.item(0), axis, Op.NewBodyFeatureOperation)
        rin.setAngleExtent(False, VI.createByString('360 deg'))
        body = revolves.add(rin).bodies.item(0)
        body.name = 'Applicator'

        # 2. Round flange, then cut flat at counter level
        sk = sketches.add(root.xYConstructionPlane)
        sk.name = 'Flange'
        circles = sk.sketchCurves.sketchCircles
        circles.addByCenterRadius(sp(sk, 0, 0, 0), mm(Rf))
        circles.addByCenterRadius(sp(sk, 0, 0, 0), mm(Ri + 2 * m))
        prof = [p for p in sk.profiles if p.profileLoops.count == 2][0]
        extrude(prof, FLANGE_T, Op.JoinFeatureOperation, bodies=[body])

        sk = sketches.add(root.xYConstructionPlane)
        sk.name = 'Flat bottom'
        sk.sketchCurves.sketchLines.addTwoPointRectangle(
            sp(sk, -Rf - 10, -Rf - 10, 0), sp(sk, Rf + 10, -BASE, 0))
        inp = extrudes.createInput(sk.profiles.item(0), Op.CutFeatureOperation)
        inp.setAllExtent(adsk.fusion.ExtentDirections.SymmetricExtentDirection)
        inp.participantBodies = [body]
        extrudes.add(inp)

        # 3. Foot: flat plate on the counter, running forward under the tube
        yc = -BASE + FOOT_T / 2
        sk = sketches.add(offset_plane(root.xZConstructionPlane, yc))
        sk.name = 'Foot'
        w, L, R = FOOT_W / 2, FOOT_LEN, FOOT_R
        lines = sk.sketchCurves.sketchLines
        arcs = sk.sketchCurves.sketchArcs
        back = lines.addByTwoPoints(sp(sk, -w, yc, 0), sp(sk, w, yc, 0))
        right = lines.addByTwoPoints(back.endSketchPoint, sp(sk, w, yc, L - R))
        front = lines.addByTwoPoints(sp(sk, w - R, yc, L), sp(sk, -w + R, yc, L))
        left = lines.addByTwoPoints(sp(sk, -w, yc, L - R), back.startSketchPoint)
        arcs.addByThreePoints(right.endSketchPoint,
                              sp(sk, w - R + R * k, yc, L - R + R * k), front.startSketchPoint)
        arcs.addByThreePoints(front.endSketchPoint,
                              sp(sk, -w + R - R * k, yc, L - R + R * k), left.startSketchPoint)
        extrude(sk.profiles.item(0), FOOT_T, Op.JoinFeatureOperation,
                symmetric=True, bodies=[body])

        # 4. Web from the foot up into the tube wall. It stands on the flange
        # (nothing to bridge when printing) and stays clear of the bell mouth.
        sk = sketches.add(root.yZConstructionPlane)
        sk.name = 'Web'
        z0 = FLANGE_T
        y_top = -(Ri + WALL * 0.6)
        poly(sk, [(0, -BASE + FOOT_T - 1, z0), (0, y_top, z0),
                  (0, y_top, z0 + WEB_LEN), (0, -BASE + FOOT_T - 1, z0 + WEB_LEN)])
        extrude(sk.profiles.item(0), WEB_T, Op.JoinFeatureOperation,
                symmetric=True, bodies=[body])

        # 5. Screw holes in the foot ears (cut only through the foot)
        sk = sketches.add(offset_plane(root.xZConstructionPlane, yc))
        sk.name = 'Ear holes'
        for x in (-(w - 12), w - 12):
            sk.sketchCurves.sketchCircles.addByCenterRadius(
                sp(sk, x, yc, FLANGE_T + 15), mm(EAR_HOLE_D / 2))
        profs = adsk.core.ObjectCollection.create()
        for p in sk.profiles:
            profs.add(p)
        extrude(profs, FOOT_T + 2, Op.CutFeatureOperation, symmetric=True, bodies=[body])

        app.activeViewport.fit()

    except Exception:
        if ui:
            ui.messageBox('Failed:\n{}'.format(traceback.format_exc()))
