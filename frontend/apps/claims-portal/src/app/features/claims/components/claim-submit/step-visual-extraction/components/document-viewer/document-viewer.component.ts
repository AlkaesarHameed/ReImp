/**
 * Document Viewer Component.
 *
 * Canvas-based component for rendering document pages with extraction overlays.
 * Displays page images with color-coded confidence regions for visual verification.
 *
 * Source: Design Document 10 - Visual Extraction Display
 * Verified: 2025-12-24
 */
import {
  Component,
  Input,
  Output,
  EventEmitter,
  ViewChild,
  ElementRef,
  AfterViewInit,
  OnChanges,
  SimpleChanges,
  ChangeDetectionStrategy,
} from '@angular/core';
import { CommonModule } from '@angular/common';

/**
 * Bounding box for text region positioning (normalized 0-1 coordinates).
 */
export interface BoundingBox {
  x: number;
  y: number;
  width: number;
  height: number;
}

/**
 * Text region with position and confidence.
 */
export interface TextRegion {
  id: string;
  text: string;
  confidence: number;
  bounding_box: BoundingBox;
  category?: string;
  field_name?: string;
}

@Component({
  selector: 'app-document-viewer',
  standalone: true,
  imports: [CommonModule],
  template: `
    <div class="document-viewer" #container>
      @if (isLoading) {
        <div class="loading-overlay">
          <i class="pi pi-spin pi-spinner"></i>
          <span>Loading document...</span>
        </div>
      }
      @if (error) {
        <div class="error-overlay">
          <i class="pi pi-exclamation-triangle"></i>
          <span>{{ error }}</span>
        </div>
      }
      <canvas
        #canvas
        [style.cursor]="'crosshair'"
        (click)="onCanvasClick($event)"
      ></canvas>
    </div>
  `,
  styles: [`
    .document-viewer {
      position: relative;
      width: 100%;
      height: 100%;
      overflow: auto;
      background: #e0e0e0;
      display: flex;
      justify-content: center;
      align-items: flex-start;
      padding: 1rem;
    }

    canvas {
      display: block;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
      background: white;
    }

    .loading-overlay,
    .error-overlay {
      position: absolute;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.5rem;
      color: #666;
      font-size: 0.9rem;
    }

    .loading-overlay i {
      font-size: 2rem;
      color: #007bff;
    }

    .error-overlay {
      color: #dc3545;
    }

    .error-overlay i {
      font-size: 2rem;
    }
  `],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class DocumentViewerComponent implements AfterViewInit, OnChanges {
  /** URL of the page image to display. */
  @Input() pageImage: string = '';

  /** Text regions to overlay on the document. */
  @Input() regions: TextRegion[] = [];

  /** Current zoom level (percentage). */
  @Input() zoomLevel: number = 100;

  /** Currently selected region. */
  @Input() selectedRegion: TextRegion | null = null;

  /** Emits when a region is clicked. */
  @Output() regionClick = new EventEmitter<TextRegion>();

  @ViewChild('canvas') canvasRef!: ElementRef<HTMLCanvasElement>;
  @ViewChild('container') containerRef!: ElementRef<HTMLDivElement>;

  isLoading = false;
  error: string | null = null;

  private ctx: CanvasRenderingContext2D | null = null;
  private image: HTMLImageElement | null = null;
  private imageLoaded = false;

  ngAfterViewInit(): void {
    const canvas = this.canvasRef?.nativeElement;
    if (canvas) {
      this.ctx = canvas.getContext('2d');
      this.loadImage();
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['pageImage'] && !changes['pageImage'].firstChange) {
      this.loadImage();
    } else if (
      (changes['zoomLevel'] || changes['regions'] || changes['selectedRegion']) &&
      this.imageLoaded
    ) {
      this.render();
    }
  }

  private loadImage(): void {
    if (!this.pageImage) {
      return;
    }

    this.isLoading = true;
    this.error = null;
    this.imageLoaded = false;

    this.image = new Image();
    this.image.crossOrigin = 'anonymous';

    this.image.onload = () => {
      this.isLoading = false;
      this.imageLoaded = true;
      this.render();
    };

    this.image.onerror = () => {
      this.isLoading = false;
      this.error = 'Failed to load document image';
    };

    this.image.src = this.pageImage;
  }

  private render(): void {
    if (!this.image || !this.ctx || !this.canvasRef) {
      return;
    }

    const canvas = this.canvasRef.nativeElement;
    const scale = this.zoomLevel / 100;
    const width = this.image.width * scale;
    const height = this.image.height * scale;

    // Set canvas size
    canvas.width = width;
    canvas.height = height;

    // Clear and draw image
    this.ctx.clearRect(0, 0, width, height);
    this.ctx.drawImage(this.image, 0, 0, width, height);

    // Draw extraction overlays
    for (const region of this.regions) {
      this.drawRegion(region, width, height);
    }
  }

  private drawRegion(region: TextRegion, canvasWidth: number, canvasHeight: number): void {
    if (!this.ctx) return;

    const box = region.bounding_box;
    const x = box.x * canvasWidth;
    const y = box.y * canvasHeight;
    const w = box.width * canvasWidth;
    const h = box.height * canvasHeight;

    // Confidence-based color
    const isSelected = region === this.selectedRegion ||
      (this.selectedRegion && region.id === this.selectedRegion.id);
    const alpha = isSelected ? 0.5 : 0.25;

    if (region.confidence >= 0.8) {
      this.ctx.fillStyle = `rgba(40, 167, 69, ${alpha})`; // Green - high confidence
    } else if (region.confidence >= 0.5) {
      this.ctx.fillStyle = `rgba(255, 193, 7, ${alpha})`; // Yellow - medium confidence
    } else {
      this.ctx.fillStyle = `rgba(220, 53, 69, ${alpha})`; // Red - low confidence
    }

    this.ctx.fillRect(x, y, w, h);

    // Border for selected region
    if (isSelected) {
      this.ctx.strokeStyle = '#0d6efd';
      this.ctx.lineWidth = 3;
      this.ctx.strokeRect(x, y, w, h);
    } else {
      // Subtle border for all regions
      this.ctx.strokeStyle = 'rgba(0, 0, 0, 0.3)';
      this.ctx.lineWidth = 1;
      this.ctx.strokeRect(x, y, w, h);
    }
  }

  onCanvasClick(event: MouseEvent): void {
    if (!this.image || !this.canvasRef) return;

    const canvas = this.canvasRef.nativeElement;
    const rect = canvas.getBoundingClientRect();
    const scale = this.zoomLevel / 100;

    // Calculate normalized coordinates
    const canvasX = event.clientX - rect.left;
    const canvasY = event.clientY - rect.top;
    const normalizedX = canvasX / (this.image.width * scale);
    const normalizedY = canvasY / (this.image.height * scale);

    // Find clicked region (check from top to bottom, last drawn is on top)
    for (let i = this.regions.length - 1; i >= 0; i--) {
      const region = this.regions[i];
      const box = region.bounding_box;

      if (
        normalizedX >= box.x &&
        normalizedX <= box.x + box.width &&
        normalizedY >= box.y &&
        normalizedY <= box.y + box.height
      ) {
        this.regionClick.emit(region);
        return;
      }
    }

    // Clicked outside any region - deselect
    this.regionClick.emit(undefined as unknown as TextRegion);
  }

  /**
   * Get the confidence level class for a given confidence score.
   */
  getConfidenceClass(confidence: number): string {
    if (confidence >= 0.8) return 'confidence-high';
    if (confidence >= 0.5) return 'confidence-medium';
    return 'confidence-low';
  }
}
