import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { TexttagEditorComponent } from './texttag-editor.component';

describe('TexttagEditorComponent', () => {
  let component: TexttagEditorComponent;
  let fixture: ComponentFixture<TexttagEditorComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ TexttagEditorComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(TexttagEditorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
